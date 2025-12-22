import sys
import os
import json
import re
import importlib.util
from typing import Optional, Dict, Any, List

# External libraries
import oci
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Load MCPClient from '5-1-client.py'
# ---------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
client_module_path = os.path.join(current_dir, "5-1-client.py")

spec = importlib.util.spec_from_file_location("mcp_client_module", client_module_path)
mcp_client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_client_module)

MCPClient = mcp_client_module.MCPClient

# ---------------------------------------------------------
# Configuration & Models
# ---------------------------------------------------------

load_dotenv(os.path.join(os.path.dirname(current_dir), ".env"))

class AgentDecision(BaseModel):
    thought: str = Field(..., description="The reasoning behind the decision.")
    use_tool: bool = Field(..., description="Whether to use a tool.")
    tool_name: Optional[str] = Field(None, description="Name of the tool to use.")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="Arguments for the tool.")
    final_response: Optional[str] = Field(None, description="Final response to the user.")

# ---------------------------------------------------------
# OCI GenAI Helpers
# ---------------------------------------------------------
def get_oci_generative_ai_inference_client(service_endpoint):
    signer = None
    config = None
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        print("[Auth] Using Resource Principal")
        return oci.generative_ai_inference.GenerativeAiInferenceClient({}, signer=signer, service_endpoint=service_endpoint)
    except Exception: pass

    try:
        config = oci.config.from_file()
        print("[Auth] Using OCI Config File")
        return oci.generative_ai_inference.GenerativeAiInferenceClient(config, service_endpoint=service_endpoint)
    except Exception: pass

    try:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        print("[Auth] Using Instance Principal")
        return oci.generative_ai_inference.GenerativeAiInferenceClient({}, signer=signer, service_endpoint=service_endpoint)
    except Exception: pass

    print("[Error] Failed to authenticate with OCI.")
    return None

def clean_json_text(text: str) -> str:
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def call_oci_genai(client, model_id: str, compartment_id: str, system_instruction: str, user_message: str) -> AgentDecision:
    schema_json = json.dumps(AgentDecision.model_json_schema(), indent=2)
    system_prompt_with_schema = (
        f"{system_instruction}\n\n"
        "You MUST respond with a VALID JSON object matching the following schema:\n"
        f"{schema_json}\n"
        "Do NOT output anything else (like markdown code blocks or explanations) outside the JSON."
    )

    chat_request = None
    if "cohere" in model_id.lower():
        chat_details = oci.generative_ai_inference.models.CohereChatRequest(
            message=user_message, chat_history=[], is_stream=False,
            preamble_override=system_prompt_with_schema, temperature=0.0, max_tokens=1000
        )
    else:
        chat_details = oci.generative_ai_inference.models.GenericChatRequest(
            messages=[
                oci.generative_ai_inference.models.Message(role="SYSTEM", content=[oci.generative_ai_inference.models.TextContent(text=system_prompt_with_schema)]),
                oci.generative_ai_inference.models.Message(role="USER", content=[oci.generative_ai_inference.models.TextContent(text=user_message)])
            ],
            temperature=0.0, max_tokens=1000
        )

    request_body = oci.generative_ai_inference.models.ChatDetails(
        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id),
        compartment_id=compartment_id, chat_request=chat_details
    )

    try:
        response = client.chat(request_body)
        response_text = response.data.chat_response.text if "cohere" in model_id.lower() else "" 
        # (Handling generic not fully implemented for brevity as per previous step)
        
        cleaned_text = clean_json_text(response_text)
        decision = AgentDecision.model_validate_json(cleaned_text)
        return decision
    except Exception as e:
        print(f"[OCI Error] {e}")
        raise e

# ---------------------------------------------------------
# Main Application
# ---------------------------------------------------------
def main():
    # 1. Load Config
    department_id = os.getenv("COMPARTMENT_ID")
    service_endpoint = os.getenv("OCI_GENAI_SERVICE_ENDPOINT")
    model_id = os.getenv("OCI_GENAI_MODEL_ID", "cohere.command-r-plus-08-2024")

    if not department_id or not service_endpoint:
        print("Error: COMPARTMENT_ID and OCI_GENAI_SERVICE_ENDPOINT must be set.")
        sys.exit(1)

    # 2. Init OCI Client
    genai_client = get_oci_generative_ai_inference_client(service_endpoint)
    if not genai_client:
        sys.exit(1)

    # 3. Init MCP Client
    print("Initializing MCP Client...")
    mcp_client = MCPClient()
    
    try:
        mcp_client.send_request("initialize", {
            "protocolVersion": "2024-11-05", 
            "capabilities": {}, 
            "clientInfo": {"name": "oci-genai-client-prompts", "version": "1.0"}
        })
        mcp_client.send_notification("notifications/initialized", {})
        mcp_client.send_request("ping", {})

        # 4. Get Available Tools
        print("Fetching tools...")
        tools_list = mcp_client.send_request("tools/list", {})
        tools_description = json.dumps(tools_list, indent=2, ensure_ascii=False)
        print(f"Tools available: {len(tools_list.get('tools', []))}")

        # 5. Get Prompts (New in Step 5-1)
        print("Fetching prompts...")
        base_system_prompt = "You are a helpful assistant." # Fallback
        
        try:
            prompts_list_result = mcp_client.send_request("prompts/list", {})
            prompts = prompts_list_result.get("prompts", [])
            print(f"Server returned {len(prompts)} prompts.")
            
            target_prompt_name = "math_tutor"
            has_planner = any(p["name"] == target_prompt_name for p in prompts)
            
            if has_planner:
                print(f"Requesting prompt: {target_prompt_name}...")
                prompt_content = mcp_client.send_request("prompts/get", {"name": target_prompt_name})
                messages = prompt_content.get("messages", [])
                
                # Extract text from the first message content if it matches our structure
                if messages and messages[0].get("content", {}).get("type") == "text":
                    base_system_prompt = messages[0]["content"]["text"]
                    print(f"[Setup] Successfully loaded system prompt from server: {target_prompt_name}")
                else:
                    print("[Warn] Prompt structure unexpected, using fallback.")
            else:
                print(f"[Warn] Prompt '{target_prompt_name}' not found on server.")
                
        except Exception as e:
            print(f"[Warn] Failed to fetch prompts: {e}")

        # 6. Chat Loop
        print("\n--- OCI GenAI Agent Started --- (Type 'exit' to quit)")
        
        while True:
            try:
                user_input = input("User: ").strip()
            except EOFError: break
            if not user_input: continue
            if user_input.lower() == "exit": break

            # Construct System Instruction (Base Prompt + Tools)
            system_instruction = (
                f"{base_system_prompt}\n\n"
                "Available Tools:\n"
                f"{tools_description}\n\n"
                
                "Instruction for Tools:\n"
                "If the user asks something that requires a tool, set 'use_tool' to true and specify the tool name and arguments.\n"
                "If no tool is needed, set 'use_tool' to false and provide a 'final_response'.\n"
            )

            print("[Agent] Thinking...")
            decision = call_oci_genai(
                genai_client, model_id, department_id, system_instruction, user_input
            )
            print(f"[Thought] {decision.thought}")
            
            if decision.use_tool:
                print(f"[System] Calling tool: {decision.tool_name} with {decision.tool_args}")
                try:
                    tool_result = mcp_client.send_request("tools/call", {
                        "name": decision.tool_name, "arguments": decision.tool_args
                    })
                    print(f"[System] Tool Output: {tool_result}")
                    
                    tool_result_str = json.dumps(tool_result, ensure_ascii=False)
                    follow_up_user_message = (
                        f"Original User Request: {user_input}\n"
                        f"Tool Execution Result: {tool_result_str}\n"
                        "Please provide the comprehensive final answer to the user."
                    )
                    follow_up_system = (
                        "You are summarizing the result of a tool execution.\n"
                        "Provide a natural language response in 'final_response'. 'use_tool' should be false."
                    )
                    final_decision = call_oci_genai(
                        genai_client, model_id, department_id, follow_up_system, follow_up_user_message
                    )
                    print(f"[Agent] {final_decision.final_response}")
                except Exception as e:
                    print(f"[System] Tool Execution Error: {e}")
            else:
                print(f"[Agent] {decision.final_response}")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            mcp_client.process.terminate()
            mcp_client.process.wait()
        except: pass
        print("Disconnected.")

if __name__ == "__main__":
    main()
