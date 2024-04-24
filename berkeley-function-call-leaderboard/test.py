import re

# Your input string
str = "gorilla_openfunctions_v1_test_executable_parallel_multiple_function.json"

match = re.search(r'gorilla_openfunctions_v1_test_(\w+)\.json$', str)
if match:
    result = match.group(1)

