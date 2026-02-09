from PIL import Image

img = Image.new("RGB", (1080, 1080), "black")
img.save("test.png")

print("Image created successfully")