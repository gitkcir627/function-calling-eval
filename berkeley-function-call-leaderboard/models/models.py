import os
import re
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers.openai_tools import JsonOutputToolsParser
from utils.logger import logger
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI




def call_to_model(
    model_name, user_prompt, function, max_tokens, temperature, top_p, timeout, test_category
): 
    """
    Perform A single request to selected model based on the parameters.
    """
    result = None
    model_tools = None
    model = None
    model_generated_function = None
    # lang_chain supported model
    if "gpt" in model_name or "mistral" in model_name:
        model_tools = gpt_like_model_tools()
        model = model_tools.get_model(model_name)
        oai_tools = model_tools.build_openai_tools(function, model_name)
        model = model.bind_tools(oai_tools)
        #message = model_tools.build_message(user_prompt)
        prompt = ChatPromptTemplate.from_messages([
        	  ("system", "You're a helpful assistant"), 
        	  ("human", "{input}"),
          ]
        )
        parser = JsonOutputToolsParser()
        chain = prompt | model | parser
        response = None
        try:
            response = chain.invoke(user_prompt)
            logger.info("model_generated_result: " + str(response))
        except:
            logger.info("Error occur when invoke model.")

        if response != None:
            model_generated_function = model_tools.convert_to_function_call_tool_calls(response, test_category)
    elif "gorilla" in model_name:
        model_tools = gpt_like_model_tools()
        model = model_tools.get_model(model_name)
        oai_tools = model_tools.build_openai_tools(function, model_name)
        try:
            completion = model.chat.completions.create(
                model="gorilla-openfunctions-v2",
                temperature=0.0,
                messages=[{"role": "user", "content": user_prompt}],
                functions=oai_tools,
            )
            # completion.choices[0].message.content, string format of the function call 
            # completion.choices[0].message.functions, Json format of the function call
            response = completion.choices[0].message.function_call
            if response != None:
                model_generated_function = model_tools.convert_to_function_call_gorilla(response, test_category)
        except Exception as e:
            logger.info(str(e))
    else:
        logger.info("this model is not accepted now.")
        exit()
    return model_generated_function


def extract_key_values(obj, prefix=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from extract_key_values(v, prefix + k + '.')
    else:
        yield (prefix[:-1], obj)





class gpt_like_model_tools:
    def __init__(self):
        pass

    def get_model(self, model_name: str):
        model = None
        if "gpt" in model_name:
            model = ChatOpenAI(
                model=model_name, 
                temperature=0, 
                openai_api_key = os.environ.get("OPENAI_API_KEY")
                #openai_api_key = ""
            )
        elif "mistral" in model_name:
            model = ChatMistralAI(
                model=model_name, 
                #api_key="",
                endpoint=""
            )
        elif "gorilla" in model_name:
            from openai import OpenAI
            model = OpenAI(
                # This is the default and can be omitted
                api_key="EMPTY",
                base_url="http://luigi.millennium.berkeley.edu:8000/v1"
            )
        return model

    def build_message(self, user_prompt:str):
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

    def build_openai_tools(self, function, model_name):
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
            if "gorilla" in model_name:
                oai_tool.append(item)
            else:
                oai_tool.append({"type": "function", "function": item})
            #oai_tool.append(item)
        return oai_tool

    def convert_to_function_call_tool_calls(self, response, test_category):
        """
        Parse OAI param list into executable function calls.
        """
        output_func_list = []
        # Step 1: Remove the outer square brackets
        for response_tool_calls in response:
            function_name = response_tool_calls["type"]
            function_params = response_tool_calls["args"]

            first_level_key = set()
            # Extract and print all key-value pairs
            for key, value in extract_key_values(function_params):
                value = str(value)
                if "." in key:
                    first_level_key.add(key.split(".")[0])
                else:
                    first_level_key.add(key)
            first_level_key = list(first_level_key)
            function_params = str(function_params)
            for key in first_level_key:
                function_params = re.sub(f'\'{key}\'.?:', f'{key} =', function_params)
            function_params = re.sub('= ?false', '= "false"', function_params)
            function_params = re.sub('= ?true', '= "true"', function_params)
            formated_function_params = '(' + function_params[1:-1] + ')'
            formated_function_call = None
            if "rest" in test_category:
                formated_function_call = function_name.replace("_", ".") + formated_function_params
            else: 
                formated_function_call = function_name.replace(".", "_") + formated_function_params
            output_func_list.append(formated_function_call)
        # Step 7: Format the function call
        return output_func_list
    
    def convert_to_function_call_gorilla(self, response, test_category):
        output_func_list = []
        if not isinstance(response, list):
            function_name = None 
            function_params = None
            for element in response:
                if element[0] == "name":
                    function_name = element[1]
                if element[0] == "arguments":
                    function_params = element[1]
            first_level_key = set()
            # Extract and print all key-value pairs
            for key, value in extract_key_values(function_params):
                value = str(value)
                if "." in key:
                    first_level_key.add(key.split(".")[0])
                else:
                    first_level_key.add(key)
            first_level_key = list(first_level_key)
            function_params = str(function_params)
            for key in first_level_key:
                function_params = re.sub(f'\'{key}\'.?:', f'{key} =', function_params)
            function_params = re.sub('= ?false', '= "false"', function_params)
            function_params = re.sub('= ?true', '= "true"', function_params)
            formated_function_params = '(' + function_params[1:-1] + ')'
            formated_function_call = None
            if "rest" in test_category:
                formated_function_call = function_name.replace("_", ".") + formated_function_params
            else: 
                formated_function_call = function_name.replace(".", "_") + formated_function_params
            output_func_list.append(formated_function_call)
        else:
            for function_call in response:
                function_name = function_call.name
                function_params = function_call.arguments
                first_level_key = set()
                # Extract and print all key-value pairs
                for key, value in extract_key_values(function_params):
                    value = str(value)
                    if "." in key:
                        first_level_key.add(key.split(".")[0])
                    else:
                        first_level_key.add(key)
                first_level_key = list(first_level_key)
                function_params = str(function_params)
                for key in first_level_key:
                    function_params = re.sub(f'\'{key}\'.?:', f'{key} =', function_params)
                function_params = re.sub('= ?false', '= "false"', function_params)
                function_params = re.sub('= ?true', '= "true"', function_params)
                formated_function_params = '(' + function_params[1:-1] + ')'
                formated_function_call = None
                if "rest" in test_category:
                    formated_function_call = function_name.replace("_", ".") + formated_function_params
                else: 
                    formated_function_call = function_name.replace(".", "_") + formated_function_params
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