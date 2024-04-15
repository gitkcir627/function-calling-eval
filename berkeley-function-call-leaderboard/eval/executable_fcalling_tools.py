import time
import requests
import json
import re
from thefuzz import fuzz
from utils.logger import logger


def exec_function_call_api(function_call:list):
    response_list = []

    if type(function_call) == list:
        for fcall in function_call:
            fcall = fcall.replace("requests_get", "requests.get")
            if "https://geocode.maps.co" in function_call:
                time.sleep(2)
            response = eval(fcall)
            try:
                response = eval(fcall)
                if response.status_code == 200:
                    response = response.json()
            except Exception as e:
                logger.info(function_call)
                response = "function call fails with exception."

            response_list.append(response)

    return response_list
    

    
def exec_function_call(function_call:str):
    pass


def extract_key_values(obj, prefix=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from extract_key_values(v, prefix + k + '.')
    else:
        yield (prefix[:-1], obj)


def flatten_function_call_params(function_call: str):
    params_str = None
    match = re.search(r'\((.*)\)', function_call, re.DOTALL)
    if match:
        params_str = match.group(1)

    matches = re.findall(r'(\w+) ?=', params_str, re.DOTALL)

    if matches:
        for key in matches:
            params_str = re.sub(f'{key}', f'"{key}"', params_str)

    params_str = re.sub("'", '"', params_str)
    params_str = re.sub("=", ':', params_str)
    params_str = "{" + params_str + "}"

    flatted_function_call_params_dict = {}

    try:
        params_dict = json.loads(params_str)
        for key, value in extract_key_values(params_dict):
            flatted_function_call_params_dict[key] = str(value)
    except:
        flatted_function_call_params_dict = None
        logger.info("the function call params list cannot parse into dict.")

    return flatted_function_call_params_dict



def compare_function_call_str(
    ground_truth_function:list,
    model_generated_function:list
):
    compare_result_list = []
    result = None

    ground_truth_function_params_dict = flatten_function_call_params(ground_truth_function)
    model_generated_function_params_dict = flatten_function_call_params(model_generated_function)

    if model_generated_function_params_dict == None or model_generated_function_params_dict == None:
        function_similarity = fuzz.token_sort_ratio(
            ground_truth_function, 
            model_generated_function
        )
        result = True if function_similarity >= 90 else False

    else:
        if len(ground_truth_function_params_dict.keys()) - len(model_generated_function_params_dict.keys()) > 2:
            result = False

        correct_params_count = 0
        for key in model_generated_function_params_dict.keys():
            if key in ground_truth_function_params_dict:
                if ground_truth_function_params_dict[key] == model_generated_function_params_dict[key]:
                    correct_params_count += 1

        if correct_params_count == len(model_generated_function_params_dict):
            result = True
        else:
            result = False
    
    compare_result_list.append(result)
    
    return compare_result_list



def compare_function_call_executed_result(
    ground_truth_function:list,
    model_generated_function:list,
    ground_truth_function_exec_result:list, 
    model_generated_function_exec_result:list
):
    compare_result_list = []

    if len(ground_truth_function_exec_result) != len(model_generated_function_exec_result):
        compare_result_list.append(False)
        return compare_result_list
    
    for i in range(len(ground_truth_function)):
        compare_result = None
        function_similarity = fuzz.token_sort_ratio(
            ground_truth_function, 
            model_generated_function
        )
        function_comparison = True if function_similarity >= 90 else False

        exec_result_similarity = fuzz.token_sort_ratio(
            ground_truth_function_exec_result, 
            model_generated_function_exec_result
        )
        exec_result_comparison = True if exec_result_similarity >= 90 else False
        
        compare_result = True if function_comparison == True and exec_result_comparison == True else False
        compare_result_list.append(compare_result)
    
    return compare_result_list
                
        
    
    
    