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
# Load MCPClient from '3-2-client.py'
# ---------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
client_module_path = os.path.join(current_dir, "3-2-client.py")

spec = importlib.util.spec_from_file_location("mcp_client_module", client_module_path)
mcp_client_module = importlib.util.module_from_spec(spec)
sys.modules["mcp_client_module"] = mcp_client_module
spec.loader.exec_module(mcp_client_module)

MCPClient = mcp_client_module.MCPClient

# ---------------------------------------------------------
# Configuration & Models
# ---------------------------------------------------------

# Try to load .env file
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
    """
    Tries to authenticate using:
    1. Resource Principal
    2. Config file (~/.oci/config)
    3. Instance Principal
    """
    signer = None
    config = None

    # 1. Resource Principal
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        print("[Auth] Using Resource Principal")
        return oci.generative_ai_inference.GenerativeAiInferenceClient(
            {}, signer=signer, service_endpoint=service_endpoint
        )
    except Exception:
        pass

    # 2. Config File
    try:
        config = oci.config.from_file() # Default location
        print("[Auth] Using OCI Config File")
        return oci.generative_ai_inference.GenerativeAiInferenceClient(
            config, service_endpoint=service_endpoint
        )
    except Exception:
        pass

    # 3. Instance Principal
    try:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        print("[Auth] Using Instance Principal")
        return oci.generative_ai_inference.GenerativeAiInferenceClient(
            {}, signer=signer, service_endpoint=service_endpoint
        )
    except Exception:
        pass

    print("[Error] Failed to authenticate with OCI.")
    return None

def clean_json_text(text: str) -> str:
    """Removes Markdown code blocks (```json ... ```) from text."""
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def call_oci_genai(
    client, 
    model_id: str, 
    compartment_id: str, 
    system_instruction: str, 
    user_message: str
) -> AgentDecision:
    
    # Construct the full prompt structure (Simplified for Chat API)
    # Note: Depending on the specific model, the chat API handling might differ slightly.
    # We will use CohereChatRequest if "cohere" is in model_id, otherwise Generic.
    
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
            message=user_message,
            chat_history=[], # Stateful chat not implemented for this simple loop
            is_stream=False,
            preamble_override=system_prompt_with_schema,
            temperature=0.0, # Deterministic for tool usage
            max_tokens=1000
        )
    else:
        # Fallback for Generic / Llama etc (might need different payload structure)
        # Using GenericChatRequest as a placeholder
        chat_details = oci.generative_ai_inference.models.GenericChatRequest(
            messages=[
                oci.generative_ai_inference.models.Message(
                    role="SYSTEM", content=[oci.generative_ai_inference.models.TextContent(text=system_prompt_with_schema)]
                ),
                oci.generative_ai_inference.models.Message(
                    role="USER", content=[oci.generative_ai_inference.models.TextContent(text=user_message)]
                )
            ],
            temperature=0.0,
            max_tokens=1000
        )

    request_body = oci.generative_ai_inference.models.ChatDetails(
        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id),
        compartment_id=compartment_id,
        chat_request=chat_details
    )

    try:
        response = client.chat(request_body)
        
        # Extract text based on model type
        response_text = ""
        if "cohere" in model_id.lower():
            # Cohere response structure
            response_text = response.data.chat_response.text
        else:
            # Generic response structure (typically choices[0].message.content)
            # This part is illustrative; refer to SDK docs for exact Llama/Generic output
            # Assuming simplified access if SDK normalizes it
            pass 
            
        # Clean and Parse
        cleaned_text = clean_json_text(response_text)
        print(f"[Debug] Raw LLM Output: {cleaned_text}") # Uncomment for debugging
        
        decision = AgentDecision.model_validate_json(cleaned_text)
        return decision

    except Exception as e:
        print(f"[OCI Error] {e}")
        # Return a safe fallback or re-raise
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
        print("Please create a .env file based on .env.template or set environment variables.")
        sys.exit(1)

    # 2. Init OCI Client
    genai_client = get_oci_generative_ai_inference_client(service_endpoint)
    if not genai_client:
        sys.exit(1)

    # 3. Init MCP Client
    print("Initializing MCP Client...")
    mcp_client = MCPClient()
    
    try:
        # Handshake
        mcp_client.send_request("initialize", {
            "protocolVersion": "2025-11-25", 
            "capabilities": {}, 
            "clientInfo": {"name": "oci-genai-client", "version": "1.0"}
        })
        mcp_client.send_notification("notifications/initialized", {})
        mcp_client.send_request("ping", {})

        # 4. Get Available Tools
        print("Fetching tools...")
        tools_list = mcp_client.send_request("tools/list", {})
        tools_description = json.dumps(tools_list, indent=2, ensure_ascii=False)
        print(f"Tools available: {len(tools_list.get('tools', []))}")

        # 5. Chat Loop
        print("\n--- OCI GenAI Agent Started --- (Type 'exit' to quit)")
        
        while True:
            try:
                user_input = input("User: ").strip()
            except EOFError:
                break
                
            if not user_input:
                continue
            if user_input.lower() == "exit":
                break

            # --- Step A: Decision ---
            system_instruction = (
                "You are a helpful assistant with access to the following tools:\n"
                f"{tools_description}\n\n"
                "If the user asks something that requires a tool, set 'use_tool' to true and specify the tool name and arguments.\n"
                "If no tool is needed, set 'use_tool' to false and provide a 'final_response'.\n"
                "If a tool is used, do NOT provide a 'final_response' yet."
            )

            print("[Agent] Thinking...")
            decision = call_oci_genai(
                genai_client, model_id, department_id, system_instruction, user_input
            )
            
            print(f"[Thought] {decision.thought}")
            
            # --- Step B: Execution ---
            if decision.use_tool:
                print(f"[System] Calling tool: {decision.tool_name} with {decision.tool_args}")
                
                try:
                    tool_result = mcp_client.send_request("tools/call", {
                        "name": decision.tool_name,
                        "arguments": decision.tool_args
                    })
                    print(f"[System] Tool Output: {tool_result}")
                    
                    # Call LLM again with result
                    # For this simple loop, we just generate a final response based on the result.
                    tool_result_str = json.dumps(tool_result, ensure_ascii=False)
                    follow_up_user_message = (
                        f"Original User Request: {user_input}\n"
                        f"Tool Execution Result: {tool_result_str}\n"
                        "Please provide the comprehensive final answer to the user."
                    )
                    
                    # We can reuse the same function but the prompt logic is slightly different for follow-up.
                    # Or we can just ask for a final response now.
                    # To keep it simple, we use the same call_oci_genai but expect only final_response.
                    
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
                    print("[Agent] I encountered an error while running the tool.")
            
            else:
                # No tool used
                print(f"[Agent] {decision.final_response}")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            mcp_client.process.terminate()
            mcp_client.process.wait()
        except:
            pass
        print("Disconnected.")

if __name__ == "__main__":
    main()
