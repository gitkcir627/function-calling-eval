import os
import re
import json
from tqdm import tqdm
import requests
import argparse
from dataclasses import asdict
from anthropic import Anthropic
from utils.logger import logger
from models import models
from thefuzz import fuzz
from eval import executable_fcalling_tools

def get_args():
    parser = argparse.ArgumentParser()
    # Refer to model_choice for supported models.
    parser.add_argument("--model", type=str, default="gorilla-openfunctions-v2")
    # Refer to test_categories for supported categories.
    parser.add_argument("--test_category", type=str, default="all")

    # Parameters for the model that you want to test.
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--top_p", type=float, default=1)
    parser.add_argument("--max_tokens", type=int, default=1200)
    parser.add_argument("--num-gpus", default=1, type=int)
    parser.add_argument("--timeout", default=60, type=int)

    args = parser.parse_args()
    return args

test_categories = {
    "executable_simple": "gorilla_openfunctions_v1_test_executable_simple.json",
    "executable_parallel_function": "gorilla_openfunctions_v1_test_executable_parallel_function.json",
    "executable_multiple_function": "gorilla_openfunctions_v1_test_executable_multiple_function.json",
    "executable_parallel_multiple_function": "gorilla_openfunctions_v1_test_executable_parallel_multiple_function.json",
    "simple": "gorilla_openfunctions_v1_test_simple.json",
    "relevance": "gorilla_openfunctions_v1_test_relevance.json",
    "parallel_function": "gorilla_openfunctions_v1_test_parallel_function.json",
    "multiple_function": "gorilla_openfunctions_v1_test_multiple_function.json",
    "parallel_multiple_function": "gorilla_openfunctions_v1_test_parallel_multiple_function.json",
    "java": "gorilla_openfunctions_v1_test_java.json",
    "javascript": "gorilla_openfunctions_v1_test_javascript.json",
    "rest": "gorilla_openfunctions_v1_test_rest.json",
    "sql": "gorilla_openfunctions_v1_test_sql.json",
    "chatable": "gorilla_openfunctions_v1_test_chatable.json",
}

executable_categories = {
    "executable_simple": "gorilla_openfunctions_v1_test_executable_simple.json",
    "executable_parallel_function": "gorilla_openfunctions_v1_test_executable_parallel_function.json",
    "executable_multiple_function": "gorilla_openfunctions_v1_test_executable_multiple_function.json",
    "executable_parallel_multiple_function": "gorilla_openfunctions_v1_test_executable_parallel_multiple_function.json",
    "rest": "gorilla_openfunctions_v1_test_rest.json",
}

model_choice = {
    "gorilla-openfunctions-v0": "http://luigi.millennium.berkeley.edu:8000/v1",
    "gorilla-openfunctions-v1": "http://luigi.millennium.berkeley.edu:8000/v1",
    "gorilla-openfunctions-v2": "FILL_UP_HOSTING_HERE",
    "gpt-3.5-turbo-0613": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106": "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125": "gpt-3.5-turbo-0125",
    "gpt-4-0613": "gpt-4-0613",
    "gpt-4-1106-preview": "gpt-4-1106-preview",
    "gpt-4-0125-preview": "gpt-4-0125-preview",
    "mistral-medium": "mistral-medium",
    "mistral-large": "mistral-large",
    "mistral-tiny": "mistral-tiny",
    "mistrl-small": "mistral-small",
    "fireworks-ai": "https://api.fireworks.ai/inference/v1",
    "Nexusflow-Raven-v2": "http://38.142.9.20:10240",
    "claude-2.1": "claude-2.1",
    "claude-instant-1.2": "claude-instant-1.2",
    "deepseek-7b": "deepseek-ai/deepseek-coder-7b-instruct-v1.5",
    "glaiveai": "glaiveai/glaive-function-calling-v1",
    "llama-v2-7b": "meta-llama/Llama-2-7b",
    "llama-v2-13b": "meta-llama/Llama-2-13b",
    "llama-v2-70b": "meta-llama/Llama-2-70b",
    "dolphin-2.2.1-mistral-7b": "cognitivecomputations/dolphin-2.2.1-mistral-7b",
}

# supported open source models
model_id_dict = {
    "deepseek-7b": "deepseek-coder",
    "glaiveai": "vicuna_1.1",
    "llama-v2-7b": "llama-2",
    "llama-v2-13b": "llama-2",
    "llama-v2-70b": "llama-2",
    "dolphin-2.2.1-mistral-7b": "dolphin-2.2.1-mistral-7b",
    "gorilla-openfunctions-v0": "gorilla",
}


if __name__ == "__main__":
    args = get_args()
    model = args.model
    test_category = args.test_category
    #client = models.build_client(args.model)
    if all([model_name not in args.model for model_name in ["firework","gpt", "llama", "claude","mistral-medium","Nexus","openfunctions","mistral-medium","mistral-tiny","mistral-small","gorilla","mistral-large-latest"]]):
        if model in model_id_dict:
            model_id = model_id_dict[model]
            model_path = model_choice[model]
            if not os.path.exists("./result/" + model):
                os.makedirs("./result/" + model)
            answer_file = "./result/" + model + "/result.json"
            os.system(f"python openfunctions_evaluation_vllm.py --model-path {model_path} --model-id {model_id} --question-file eval_data_total.json --answer-file {answer_file} --num-gpus {args.num_gpus}")
    else:
        if args.test_category == "all":
            logger.info("test_category: all")
            files_to_open = list(test_categories.values())
        elif args.test_category == "executable":
            logger.info("test_category: executable")
            files_to_open = list(executable_categories.values())
        else:
            logger.info("test_category: " + args.test_category)
            files_to_open = [test_categories[args.test_category]]

        for file_to_open in files_to_open:
            logger.info("Generating: " + file_to_open)
            # get the test_case
            test_cases = []
            with open("./data/function_benchmark_dataset/" + file_to_open) as f:
                for line in f:
                    test_cases.append(json.loads(line))

            num_existing_result = 0  # if the result file already exists, skip the test cases that have been tested.
            if os.path.exists(
                "./result/" + args.model + "/" + file_to_open.replace(".json", "_result.json")
            ):
                with open(
                    "./result/"
                    + args.model
                    + "/"
                    + file_to_open.replace(".json", "_result.json")
                ) as f:
                    for line in f:
                        num_existing_result += 1

            total = 0
            success = 0
            for index, test_case in enumerate(tqdm(test_cases)):
                total += 1
                user_question = (
                    test_case["question"]
                    if type(test_case["question"]) is str
                    else test_case["question"][0]
                )
                function = (
                    [test_case["function"]]
                    if type(test_case["function"]) is dict
                    else test_case["function"]
                )
                
                ground_truth_function = []
                model_generated_function = []

                if isinstance(test_case["human_eval_answer"], str):
                    ground_truth_function = [test_case["human_eval_answer"]]
                else:
                    ground_truth_function = test_case["human_eval_answer"]
                
                model_generated_function = models.call_to_model(
                    model,
                    user_question,
                    function,
                    args.max_tokens,
                    args.temperature,
                    args.top_p,
                    args.timeout,
                )
                if model_generated_function != None:
                    logger.info("model_generated_function : \n" + str(model_generated_function[0]))
                else:
                    logger.info("model_generated_function : None")

                if "rest" in test_category and model_generated_function != None:
                    compare_result_list = executable_fcalling_tools.compare_function_call_str(
                        ground_truth_function[0],
                        model_generated_function[0]
                    )
                    
                    if False in compare_result_list or len(compare_result_list) == 0:
                        pass
                    else: 
                        success += 1
                        logger.info("current matched count: " + str(success))
                    

                    if not os.path.exists("./result/" + args.model):
                        os.makedirs("./result/" + args.model)
                    with open(
                        "./result/"
                        + args.model
                        + "/"
                        + file_to_open.replace(".json", "_result.json"),
                        "w",
                    ) as f:
                        json.dump(
                            {
                                "question": user_question,
                                "function": function,
                                "ground_truth_func": ground_truth_function,
                                "model_generated_func": model_generated_function,
                            },
                            f,
                        )
                        f.write("\n")
                
        logger.info("Accuracy: " + str(round(success/total, 2)) + "\n-----------------------")








'''
def get_gorilla_response(prompt, function, model, temperature):
    requestData = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "functions": function,
        "temperature": temperature,
    }
    url = "https://luigi.millennium.berkeley.edu:443/v1/chat/completions"
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": "EMPTY",  # Hosted for free with ❤️ from UC Berkeley
        },
        data=json.dumps(requestData),
    )
    jsonResponse = response.json()
    directCode = jsonResponse["choices"][0]["message"]["content"]
    return directCode
'''