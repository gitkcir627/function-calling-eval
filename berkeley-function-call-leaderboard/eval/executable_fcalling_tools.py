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
    function_name = None
    match = re.search(r'(.+)\((.*)\)', function_call, re.DOTALL)
    if match:
        function_name = match.group(1)
        params_str = match.group(2)

    matches = re.findall(r'(\w+) ?=', params_str, re.DOTALL)

    if matches:
        for key in matches:
            params_str = re.sub(f'{key}', f'"{key}"', params_str)

    params_str = re.sub("'", '"', params_str)
    params_str = re.sub("=", ':', params_str)
    params_str = "{" + params_str + "}"

    flattened_function_call_params_dict = {}

    try:
        params_dict = json.loads(params_str)
        for key, value in extract_key_values(params_dict):
            flattened_function_call_params_dict[key] = str(value)
    except:
        flattened_function_call_params_dict = None
        logger.info("the function call params list cannot parse into dict.")

    flattened_function = {"function_name": function_name, "params_dict": flattened_function_call_params_dict}
    return flattened_function



def compare_function_call_str(
    ground_truth_functions:list,
    model_generated_functions:list
):
    compare_result_list = []

    if len(ground_truth_functions) != len(model_generated_functions):
        return compare_result_list.append(False)
    
    #sorted by function_name
    ground_truth_functions = sorted(ground_truth_functions, key=lambda x: x.split("(")[0])
    model_generated_functions = sorted(ground_truth_functions, key=lambda x: x.split("(")[0])

    ground_truth_flattened_function_params = []
    for ground_truth_function in ground_truth_functions:
        flattened_function = flatten_function_call_params(ground_truth_function)
        ground_truth_flattened_function_params.append(flattened_function["params_dict"])

    model_generated_flattened_functions_params = []
    for model_generated_function in model_generated_functions:
        flattened_function = flatten_function_call_params(model_generated_function)
        model_generated_flattened_functions_params.append(flattened_function["params_dict"])

    # take param list from the same function_name to compare
    for i in range(len(ground_truth_flattened_function_params)):
        compare_result = None
        ground_truth_function_params_dict = ground_truth_flattened_function_params[i]
        model_generated_function_params_dict = model_generated_flattened_functions_params[i]

        try:
            if model_generated_function_params_dict == None or ground_truth_function_params_dict == None:
                '''
                function_similarity = fuzz.token_sort_ratio(
                    ground_truth_functions, 
                    model_generated_functions
                )
                result = True if function_similarity >= 90 else False
                '''
            else:
                if len(ground_truth_function_params_dict.keys()) - len(model_generated_function_params_dict.keys()) > 2:
                    compare_result = False

                correct_params_count = 0
                for key in model_generated_function_params_dict.keys():
                    if key in ground_truth_function_params_dict:
                        if ground_truth_function_params_dict[key] == model_generated_function_params_dict[key]:
                            correct_params_count += 1

                logger.info("model_generated_function_params_pair_count: " + str(len(model_generated_function_params_dict)))
                logger.info("correct_params_count: " + str(correct_params_count))
                if correct_params_count == len(model_generated_function_params_dict):
                    compare_result = True
                else:
                    compare_result = False
        except:
            compare_result = False
            logger.info("an error occur when compare the ground_truth_function and model_generated_function.")

        compare_result_list.append(compare_result)
    
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
                
        
    
    
    