import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
url = "http://192.168.1.1:8888"
# 1. Initialize the browser
driver = webdriver.Chrome()
driver.get(url)

# 2. Wait for elements to be present to avoid timing errors
wait = WebDriverWait(driver, 10)
input1 = wait.until(EC.presence_of_element_located((By.ID, "name")))
input2 = wait.until(EC.presence_of_element_located((By.ID, "password")))
submit_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "toolbar")))

# 3. Fill the input fields
input1.send_keys("admin")
input2.send_keys("admin")

# 4. Click the button to trigger the function
submit_btn.click()

# 5. Get the response
# If the function updates the same page, get the new HTML
response_html = driver.page_source
print(response_html)

# If the function opens a new tab or downloads a file, handle accordingly
# driver.quit() # Close the browser when done   


