import os
import json
data = []
"""
    Compile evaluation data into a single file
"""
for filename in os.listdir("./function_benchmark_dataset/"):
    if "gorilla" in filename:
        with open(f"./function_benchmark_dataset/{filename}", "r") as file:
            for line in file:
                item = json.loads(line)
                name = filename.replace("gorilla_openfunctions_v1_test_","").replace(".json","")
                item["question_type"] = name
                data.append(item)
with open("./eval_data_total.json", "a+") as file:
    for item in data:
        file.write(json.dumps(item))
        file.write("\n")
print("Data successfully compiled into eval_data_total.json 🦍")