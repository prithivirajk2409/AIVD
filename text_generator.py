import openai, argparse, re
from api_key import API_KEY
openai.api_key = API_KEY
model_engine = "text-davinci-003"

parser = argparse.ArgumentParser()
parser.add_argument('args', nargs='*', help='all arguments passed to the script')
args = parser.parse_args()
prompt= args.args[0]
print("The AI BOT is trying now to generate a new text for you...")
completions = openai.Completion.create(
    engine=model_engine,
    prompt=prompt,
    max_tokens=1024,
    n=1,
    stop=None,
    temperature=0.5,
)
generated_text = completions.choices[0].text
with open("generated_text.txt", "w") as file:
    file.write(generated_text.strip())

print("The Text Has Been Generated Successfully!")
print("_______The Output is______")

with open('generated_text.txt', 'r') as file:
    file_contents = file.read()
    print(file_contents)

