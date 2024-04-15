import os
import re
import json
from utils.logger import logger




def call_to_model(
    model, user_prompt, function, max_tokens, temperature, top_p, timeout
): 
    """
    Perform A single request to selected model based on the parameters.
    """
    result = None
    model_tools = None
    if "gpt" in model:
        # Build OAI tool calls.
        model_tools = gpt_tools()
        client = model_tools.get_client()
        oai_tool = model_tools.build_openai_tools(function)
        message = model_tools.build_message(user_prompt)

        if len(oai_tool) > 0:       
            response = client.chat.completions.create(
                messages=message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                timeout=timeout,
                tools=oai_tool,
            )
                
            try:
                #result = model_tools.convert_to_function_call(response)
                if response.choices[0].message.tool_calls != None:
                    logger.info("tool_calls : \n" + str(response.choices[0].message.tool_calls))
                    result = model_tools.convert_to_function_call_tool_calls(response)
                else:
                    result = None
                    #result = response.choices[0].message.content
            except:
                    result = None
                    #result = response.choices[0].message.content
        '''
        elif "llama" in model:
            response = client.chat.completions.create(
                messages="llama_message",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                timeout=timeout,
                tools=oai_tool,
            )
        else:
            response = client.chat.completions.create(
                messages=message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                timeout=timeout,
            )
        '''
    else:
        logger.info("this model is not accepted now.")
        exit()
    return result


def extract_key_values(obj, prefix=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from extract_key_values(v, prefix + k + '.')
    else:
        yield (prefix[:-1], obj)





class gpt_tools:
    def __init__(self):
        pass

    def get_client(self):
        from openai import OpenAI
        client = OpenAI(api_key= os.environ.get("OPENAI_API_KEY"))
        #client = OpenAI(api_key= "")
        return client
    
    def build_message(self, user_prompt:str):
        message_with_system_prompt = [
            {"role": "system", "content": '''
                You are an expert in composing functions. You are given a question and a set of possible functions. 
                Based on the question, you will need to make one or more function/tool calls to achieve the purpose. 
                If none of the function can be used, point it out. If the given question lacks the parameters required by the function,
                also point it out. 
                the result, function call, must contain the function and it parameters, in json format.
                You should only return the function call without any redundant word or character.
                '''},
            {
                "role": "user",
                "content": "Questions:"
                + user_prompt
                + "\n Return Nothing if no tool or function calls are involved.",
            }
        ]

        message = [
            {
                "role": "user",
                "content": "Questions:"
                + user_prompt
                + "\n Return Nothing if no tool or function calls are involved.",
            }
        ]
        return message

    def _cast_multi_param_type(self, properties):
        """
        OpenAI rejects parameters type other than JSON serializable type.
        Since our evaluation contains Python specific types, we need some casting
        """
        for key, value in properties.items():
            if "type" not in value:
                properties[key]["type"] = "string"
            else:
                value["type"] = value["type"].lower()
                if value["type"] not in [
                    "object",
                    "string",
                    "number",
                    "boolean",
                    "array",
                    "integer",
                ]:
                    properties[key]["type"] = "string"
                elif value["type"] == "array" and "items" not in properties[key].keys():
                    properties[key]["items"] = {"type": "object"}
                elif value["type"] == "array" and "type" not in properties[key]["items"].keys():
                    properties[key]["items"]["type"] = "object"
                elif value["type"] == "array" and properties[key]["items"]["type"] not in [
                    "object",
                    "string",
                    "number",
                    "boolean",
                    "array",
                    "integer"
                ]:
                    properties[key]["items"]["type"] = "string"
        return properties    

    def build_openai_tools(self, function:str):
        oai_tool = []
        for item in function:
            if "." in item["name"]:
                item["name"] = re.sub(
                    r"\.", "_", item["name"]
                )  # OAI does not support "." in the function name so we replace it with "_". ^[a-zA-Z0-9_-]{1,64}$ is the regex for the name.
            item["parameters"]["type"] = "object"  # If typing is missing, we assume it is an object since OAI requires a type.
            if "properties" not in item["parameters"]:
                item["parameters"]["properties"] = item["parameters"].copy()
                item["parameters"]["type"] = "object"
                for key in list(item["parameters"].keys()).copy():
                    if key != "properties" and key != "type" and key != "required":
                        del item["parameters"][key]
                for key in list(item["parameters"]["properties"].keys()).copy():
                    if key == "required" or key == "type":
                        del item["parameters"]["properties"][key]
            item["parameters"]["properties"] = self._cast_multi_param_type(
                item["parameters"]["properties"]
            )
            oai_tool.append({"type": "function", "function": item})
        return oai_tool


    def convert_to_function_call(self, response):
        response_content = str(response.choices[0].message.content)
        response_content = response_content.replace("functions.", "")
        response_content_dict = json.loads(response_content)

        first_level_key = set()
        second_level_key = set()

        # Extract and print all key-value pairs
        for key, value in extract_key_values(response_content_dict):
            first_level_key.add(key.split(".")[0])
            second_level_key.add(key.split(".")[1])

        function_name = str(list(first_level_key)[0])
        second_level_key = list(second_level_key)

        function_params_json = json.dumps(response_content_dict[function_name])

        for key in second_level_key:
            function_params_json = re.sub(f'"{key}".?:', f'{key}=', function_params_json)

        formated_function_params = '(' + function_params_json[1:-1] + ')'

        formated_function_call = function_name + formated_function_params
        print(formated_function_call)

        return formated_function_call


    def convert_to_function_call_tool_calls(self, response):
        """
        Parse OAI param list into executable function calls.
        """
        # Step 1: Remove the outer square brackets
        response_tool_calls = str(response.choices[0].message.tool_calls[0])
        #response_tool_calls = response_tool_calls[1:-1]
        output_func_list = []

        match = re.search(r"Function\(arguments='(\{.*?\})', name='(.*?)'\)", response_tool_calls, re.DOTALL)
        function_name = None
        params_str = None
        if match:
            params_str = match.group(1).replace("\\n", "")
            function_name = match.group(2)
        first_level_key = set()
        # Extract and print all key-value pairs
        for key, value in extract_key_values(json.loads(params_str)):
            value = str(value)
            if "." in key:
                first_level_key.add(key.split(".")[0])
            else:
                first_level_key.add(key)

        first_level_key = list(first_level_key)

        function_params = params_str
        for key in first_level_key:
            function_params = re.sub(f'"{key}".?:', f'{key} =', function_params)

        function_params = re.sub('= ?false', '= "false"', function_params)
        function_params = re.sub('= ?true', '= "true"', function_params)

        formated_function_params = '(' + function_params[1:-1] + ')'

        formated_function_call = function_name.replace("_", ".") + formated_function_params

        output_func_list.append(formated_function_call)
        # Step 7: Format the function call
        return output_func_list



SYSTEM_PROMPT_FOR_CHAT_MODEL = """"
    You are an expert in composing functions. You are given a question and a set of possible functions. 
    Based on the question, you will need to make one or more function/tool calls to achieve the purpose. 
    If none of the function can be used, point it out. If the given question lacks the parameters required by the function,
    also point it out. You should only return the function call in tools call sections.
    """
USER_PROMPT_FOR_CHAT_MODEL = """
    Questions:{user_prompt}
    Here is a list of functions in JSON format that you can invoke:\n{functions}. 
    Should you decide to return the function call(s), NO other text MUST be included.
    """

class llama_tools:
    def __init__(self):
        pass

    def get_client(self):
        from openai import OpenAI
        client = OpenAI(
            base_url = 'http://localhost:11434/v1',
            api_key='ollama'
        )
        return client

    def build_message(self, user_prompt:str):
        message=[
            {"role": "system", "content": SYSTEM_PROMPT_FOR_CHAT_MODEL},
            {"role": "user", "content": 
                USER_PROMPT_FOR_CHAT_MODEL.format(
                    user_prompt=user_prompt, functions=str(function)
                )
            }
        ]
        return message

    
class gorilla_openfunctions_tools:
    pass

class mistral_tools:
    pass

class meetkai_functionary_tools:
    pass


'''
gpt-3.4
gpt-4
NonusResearch/Llama-2-70b-hf
mistral/Mixtral-8x7B-v0.1
Gorilla-OpenFunctions-v2(FC)
meetkai/functionary-small-v2.2
'''    
    

'''
def build_client(model_name):
    # Fill in the API key for the model you want to test.
    client = None
    if "gpt" in model_name:
        client = gpt_tools().get_client()
    elif "llama" in model_name:
        llama_tools = llama_tools()
        client = llama_tools.get_client()
    elif "mistral-medium" in model_name or "mistral-tiny" in model_name or "mistral-small" in model_name or "mistral-large-latest" in model_name:
        from mistralai.client import MistralClient
        client = MistralClient(api_key= os.environ.get("MISTRAL_API_KEY"))
    elif "gorilla-openfunctions-v2" in model_name:
        return None
    else:
        return None
    return client
'''