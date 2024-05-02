from models import models


model_tools = models.gpt_like_model_tools()
model = model_tools.get_model("gorilla-openfunctions-v2")

functions = [
    {
        "name": "get_uid",
        "description": "Get the uid of a person from the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "fullname": {
                    "type": "string",
                    "description": "The full name of a person.",
                },
            },
            "required": ["fullname"],
        },
    },
    {
        "name": "get_basic_info",
        "description": "Get the person basic info from the database by the person uid",
        "parameters": {
            "type": "object",
            "properties": {
                "uid": {
                    "type": "string",
                    "description": "the unique identifier, unique key of a person in the database.",
                },
            },
            "required": ["uid"]
        }
    }
]

system_prompt = '''
You are an assitant to generate function call.
for the given functions, if the user prompt requires multiple functions in sequence to achieve,
if the parameter of later function is the result of the former function, 
give the nested function like this way: function_b(function_a())
'''

user_prompt = '''
tell me the basic info about "Rick". 
'''

oai_tools = model_tools.build_openai_tools(functions, "gorilla-openfunctions-v2")

try:
    completion = model.chat.completions.create(
        model="gorilla-openfunctions-v2",
        temperature=0.0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        functions=oai_tools,
    )
    # completion.choices[0].message.content, string format of the function call 
    # completion.choices[0].message.functions, Json format of the function call
    response = completion.choices[0].message.function_call
    print(response)
    if response != None:
        model_generated_function = model_tools.convert_to_function_call_gorilla(response, "rest")
        print(model_generated_function)
except Exception as e:
    print(str(e))