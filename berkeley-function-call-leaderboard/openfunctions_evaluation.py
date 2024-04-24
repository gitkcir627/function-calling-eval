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
}


if __name__ == "__main__":
    args = get_args()
    model = args.model
    test_category = args.test_category
    #client = models.build_client(args.model)
    if args.test_category == "all":
        logger.info("test_category: all")
        files_to_open = list(test_categories.values())
    elif args.test_category == "executable":
        logger.info("test_category: executable")
        files_to_open = list(executable_categories.values())
    else:
        logger.info("test_category: " + args.test_category)
        files_to_open = [test_categories[args.test_category]]

    score_dict = {}

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

        if not os.path.exists("./result/" + args.model):
            os.makedirs("./result/" + args.model)
        
        result_file = "./result/" + args.model + "/" + file_to_open.replace(".json", "_result.json")
        if os.path.exists(result_file):
            os.remove(result_file)

        for index, test_case in enumerate(tqdm(test_cases)):
            total += 1
            user_question = (
                test_case["question"]
                if type(test_case["question"]) is str
                else test_case["question"][0]
            )
            function = (
                [test_case["function"]] if type(test_case["function"]) is dict else test_case["function"]
            )
            
            ground_truth_function = []
            model_generated_function = []
            if isinstance(test_case["human_eval_answer"], str):
                #ground_truth_function = [test_case["human_eval_answer"]]
                ground_truth_function_str = test_case["human_eval_answer"]
                ground_truth_function = re.split(r',\s*(?![^()]*\))', ground_truth_function_str.strip('[]'))
            else:
                ground_truth_function = test_case["human_eval_answer"]
            logger.info("ground_truth_function: " + str(ground_truth_function))

            model_generated_function = models.call_to_model(
                model,
                user_question,
                function,
                args.max_tokens,
                args.temperature,
                args.top_p,
                args.timeout,
                args.test_category,
            )
            if model_generated_function != None:
                logger.info("model_generated_function : \n" + str(model_generated_function))
            else:
                logger.info("model_generated_function : None")
            if ("rest" in test_category or "executable" in test_category) \
                    and model_generated_function != None and model_generated_function != []:
                compare_result_list = executable_fcalling_tools.compare_function_call_str(
                    ground_truth_function,
                    model_generated_function
                )
                
                if compare_result_list == None or False in compare_result_list or len(compare_result_list) == 0:
                    pass
                    logger.info("compare reuslt: False")
                else: 
                    success += 1
                    logger.info("compare reuslt: Ture, current matched count: " + str(success))

            with open(result_file, "a") as f:
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

        category = None
        match = re.search(r'gorilla_openfunctions_v1_test_(\w+)\.json$', file_to_open)
        if match:
            category = match.group(1)
        score_dict[category] = str(round(success/total, 2))
        logger.info("Accuracy: " + str(round(success/total, 2)) + "\n-----------------------")
    logger.info("**********************************")
    logger.info("\n--------- scores ---------\n" + str(score_dict))








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