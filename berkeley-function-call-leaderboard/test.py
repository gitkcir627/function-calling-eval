import requests 
import json
import re


def extract_key_values(obj, prefix=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from extract_key_values(v, prefix + k + '.')
    else:
        yield (prefix[:-1], obj)


def convert_to_function_call_tool_calls(response_tool_calls):
    """
    Parse OAI param list into executable function calls.
    """
    # Step 1: Remove the outer square brackets
    #model_generated_result = model_generated_response.choices[0].message.tool_calls
    response_tool_calls = response_tool_calls[1:-1]
    output_func_list = []

    match = re.search(r"Function\(arguments='(\{.*?\})', name='(.*?)'\)", response_tool_calls, re.DOTALL)
    function_name = None
    params_str = None
    if match:
        params_str = match.group(1)
        function_name = match.group(2)
    first_level_key = set()
    # Extract and print all key-value pairs
    for key, value in extract_key_values(json.loads(params_str)):
        value = str(value)
        print(key + " : " + value)
        if "." in key:
            first_level_key.add(key.split(".")[0])
        else:
            first_level_key.add(key)

    first_level_key = list(first_level_key)

    function_params = params_str
    for key in first_level_key:
        function_params = re.sub(f'"{key}".?:', f'{key} =', function_params)

    formated_function_params = '(' + function_params[1:-1] + ')'

    formated_function_call = function_name.replace("_", ".") + formated_function_params

    output_func_list.append(formated_function_call)
    # Step 7: Format the function call
    return output_func_list




str_1 = '''[ChatCompletionMessageToolCall(id='call_fVSRPDwHJwmqliQD3SoYFXMl', function=Function(arguments='{\n  "url": "https://timezone-by-location.p.rapidapi.com/timezone",\n  "headers": {\n    "X-RapidAPI-Key": "8a33a40231msh257adb8a2cc9440p10ae7cjsnf46f8c5eda1c",\n    "X-RapidAPI-Host": "timezone-by-location.p.rapidapi.com"\n  },\n  "params": {\n    "lat": 48.8584,\n    "lon": 2.2945\n  }\n}', name='requests_get'), type='function')]'''

result = convert_to_function_call_tool_calls(str_1)

response_tool_calls = str_1[1:-1]

match = re.search(r"Function\(arguments='(\{.*?\})'", str_1, re.DOTALL)
if match:
    json_str = match.group(1)

    # Fix the JSON string
    json_str = json_str.replace("\n", "")

    # Parse the JSON
    data = json.loads(json_str)
print(data)

function_name = None
params_str = None

match = re.search(r"Function\(arguments='(\{.*?\})', name='(.*?)'\)", str_1, re.DOTALL)
if match:
    params_str = match.group(1)
    params_str = params_str[1:-1]
    function_name = match.group(2)
    print(params_str)
    print(function_name)



json_data_3 = '''{
  "url": "https://timezone-by-location.p.rapidapi.com/timezone",
  "headers": {
    "X-RapidAPI-Key": "8a33a40231msh257adb8a2cc9440p10ae7cjsnf46f8c5eda1c",
    "X-RapidAPI-Host": "timezone-by-location.p.rapidapi.com"
  },
  "params": {
    "lat": 48.8584,
    "lon": 2.2945
  }
}
'''
# Convert the string to a Python dictionary
data = json.loads(json_data_3)

first_level_key = set()
# Extract and print all key-value pairs
for key, value in extract_key_values(data):
    value = str(value)
    print(key + " : " + value)
    if "." in key:
        first_level_key.add(key.split(".")[0])
    else:
        first_level_key.add(key)

first_level_key = list(first_level_key)

function_params = params_str

for key in first_level_key:
    function_params = re.sub(f'"{key}".?:', f'{key} =', function_params)

formated_function_params = '(' + function_params[1:-1] + ')'

formated_function_call = function_name.replace("_", ".") + formated_function_params

print(formated_function_call)

response = eval(formated_function_call)
if response.status_code == 200:
    response = response.json()
print(response)
