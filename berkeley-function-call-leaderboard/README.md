### quick try 
```bash
    cd berkeley-function-call-leaderboard/
    sudo docker build -t zhihao/funtion-calling-eval .

    sudo docker run \
    -it --name funtion-calling-eval --rm --privileged \
    -v $(pwd)/:/funtion-calling-eval/berkeley-function-call-leaderboard/ \
    zhihao/funtion-calling-eval bash

    #sudo docker exec -it funtion-calling-eval bash
    
    #inside the container
        cd berkeley-function-call-leaderboard/

        # set OPENAI_API_KEY
        echo "export OPENAI_API_KEY=\"value\"" >> ~/.bashrc
        source ~/.bashrc

        #fill the endpoint of this code block in models/models.py
            model = ChatMistralAI(
                model=model_name, 
                #api_key="",
                endpoint=""
            )

        # run the evaluation
        #supported_model_list:
        # gpt-*, gorilla-openfunctions-v2, mistral-*
        python openfunctions_evaluation.py --model ${model} --test_category rest --temperature 0.3
        python openfunctions_evaluation.py --model ${model} --test_category executable --temperature 0.3
        #supported_model_list:
        # gpt-*, gorilla-openfunctions-v2, mistral-*
        
```


### statistics
```text
gpt-4-0613:
rest: 0.4
executable_simple: 0.85
parallel_function: 1.00
multiple_function: 0.94
parallel_multiple_function: 1.00

gorilla:
rest: 1.0
executable_simple: '0.95', 
executable_parallel_function: '0.84', 
executable_multiple_function: '0.96', 
executable_parallel_multiple_function: '0.82'
```










### Install Dependencies

Before generating the leaderboard statistics, you should install dependencies using the following command: 

```bash
    conda create -n BFCL python=3.10
    conda activate BFCL
    pip install -r requirements.txt
    pip install vllm # If you have vLLM supported GPU(s) and want to run our evaluation data against self-hosted OSS models.
```

## Prepare Evaluation Dataset

To download the evaluation dataset from huggingface, from the current directory `./openfunctions/berkeley-function-call-leaderboard`, run the following command:

```bash
    cd berkeley-function-call-leaderboard
    huggingface-cli download gorilla-llm/Berkeley-Function-Calling-Leaderboard --local-dir ./data/function_benchmark_dataset --repo-type dataset
```

This will download our dataset to `data` repository. 

If you plan to evaluate on OSS models, we are using vLLM for inference and refer to https://github.com/vllm-project/vllm for detail. We recommend to inference on at least V100s, A100s, and latest GPUs that are supported by vLLM. 

## Execution Evaluation Data Post-processing 
Input your API keys into `function_credential_config.json`, so that the original placeholder values in questions, params, and answers will be cleaned. 

To run the executable test categories, there are 4 API keys to fill out:

1. RAPID-API Key: https://rapidapi.com/hub

    * Yahoo Finance: https://rapidapi.com/sparior/api/yahoo-finance15
    * Real Time Amazon Data : https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data
    * Urban Dictionary: https://rapidapi.com/community/api/urban-dictionary
    * Covid 19: https://rapidapi.com/api-sports/api/covid-193
    * Time zone by Location: https://rapidapi.com/BertoldVdb/api/timezone-by-location

    All the Rapid APIs we use have free tier usage. As a result, you need to subscribe to those API providers in order to have the executable test enviornment setup but it will be free of charge!

2. Exchange Rate API:https://www.exchangerate-api.com
3. OMDB API: http://www.omdbapi.com/apikey.aspx
4. Geocode API: https://geocode.maps.co/

The `apply_function_credential_config.py` inputs an input file, optionally an outputs file. If the output file is not given as an argument, it will overwrites your original file with the claned data.

```bash
    cd data/
    python apply_function_credential_config.py --input_file ./function_benchmark_dataset/gorilla_openfunctions_v1_test_rest.json
```

Then, use `eval_data_compilation.py` to compile all files by using

```bash
    python eval_data_compilation.py
```
## Berkeley Function-Calling Leaderboard Statistics

To run Mistral Models function calling, you need to have `mistralai >= 0.1.3`.

Also provide your API keys in your environment variables.

```bash
    export OPENAI_API_KEY=sk-XXXXXX
    export MISTRAL_API_KEY=XXXXXX
    export FIRE_WORKS_API_KEY=XXXXXX
    export ANTHROPIC_API_KEY=XXXXXX
```

To generate leaderboard statistics, there are two steps:

1. Inference the evaluation data and obtain the results from specific models 

```bash
    python openfunctions_evaluation.py --model MODEL_NAME --test_category TEST_CATEGORY --temperature 0.3
    python openfunctions_evaluation.py --model gpt-4-0613 --test_category rest --temperature 0.3
```
For TEST_CATEGORY, we have `executable_simple`, `executable_parallel_function`, `executable_multiple_function`, `executable_parallel_multiple_function`, `simple`, `relevance`, `parallel_function`, `multiple_function`, `parallel_multiple_function`, `java`, `javascript`, `rest`, `sql`, `chatable`.

If you want to run all evaluation at the same time, you can use `all` as the test category.

Running proprietary model like GPTs, Claude, Mistral-X will requires an API-Key which can be supplied in `openfunctions_evaluation.py`.

If decided to run OSS model, openfunctions evaluation uses vllm and therefore requires GPU for hosting and inferencing.

1. Check the accuracy of the evaluation result by our AST and Executable checks

```bash
    python openfunctions_checker.py --model MODEL_NAME --test_category {TEST_CATEGORY,all,ast,executable}
```

If you want to run the "all" or "executable" category, make sure to register your REST API keys in `function_credential_config.json`. This is because Gorilla Openfunctions Leaderboard want to test model's generated output on real world API! 

If you don't want to supply any API key, that's alright! Set `test_category` to `ast`. There, we are only doing the ast tree parsing and perform an exact match to derive the accuracy.

The output of this is in the format of 
```
Testing type: XXX, success rate: XXX
```

To ease the usage for generating and evaluating results on a range of models and test categories, we provide a script `test_eval_api.sh` that can be used to generate evaluation results for all model provided in the list parallelly. Before running the bash file, make sure to fill in the API keys.

```bash
    bash test_eval_api.sh
```
If you are using oss, feel free to use `bash test_eval_oss.sh` with appropriated parameteres

After generation evaluation results, you can use `test_eval_checker.sh` to check the accuracy of the evaluation result by our AST and Executable checks, select your evaluation method. 

```bash
    bash test_eval_checker.sh
```


## Models Available
Below is a list of model we support to run our leaderboard evaluation against. If supported function calling, we will follow its function calling format provided by official documentations. Else, we will construct system message to prompt the model to generate function calls in the right format.
|Model | Function Calling |
|---|---|
|gorilla-openfunctions-v2 | Supported|
|gpt-3.5-{turbo-0613, turbo-1106, turbo-0125}| Supported|
|gpt-4-{0613, 1106-preview, 0125-preview}| Supported|
|glaiveai 💻|  Supported| 
|Nexusflow-Raven-v2| Supported|
|fireworks-ai | Supported|
|mistral-large-2402 | Supported|
|claude-{2.1,instant-1.2}| Not supported|
|mistral-{tiny,small,medium}| Not supported|
|deepseek-7b 💻| Not supported|
|llama-v2-{7b,13b,70b} 💻| Not supported|

Here {MODEL}💻 means the model needs to be hosted locally and called by vllm, {MODEL} means the models that are called API calls.

If you are thinking about adding more OSS models to evaluate. Here are the codes you need to change 
* In `openfunctions_evaluation.py`, add `model_name` and `model_id` to `model_id_dict`. Check vllm for more details of what to put.
* In `openfunctions_ast_checker.py`, add parser that parse model output in the format of either JSON schema or function calling schema(i.e. `[func1(param1=val1...)...]`).
*  In `openfunctions_executable_checker.py`, make sure  to parse the model output in the format of list of function calls string i.e. `["func_call_1","func_call_2"...]` where `func_call_n` is executable strings using `exec()`


## Changelog
* [#237](https://github.com/ShishirPatil/gorilla/pull/237) and [238](https://github.com/ShishirPatil/gorilla/pull/238) leaderboard update resulting from [#223](https://github.com/ShishirPatil/gorilla/pull/223); 3 new models: `mistral-large-2402`, `gemini-1.0-pro`, and `gemma`.
* [#223](https://github.com/ShishirPatil/gorilla/pull/223) modifications to REST evaluation. 


## Contributing

All the leaderboard statistics, and data used to train the models is released under Apache 2.0.
Gorilla is an open source effort from UC Berkeley and we welcome contributors. 
Please email us your comments, criticism, and questions. More information about the project can be found at [https://gorilla.cs.berkeley.edu/](https://gorilla.cs.berkeley.edu/)

