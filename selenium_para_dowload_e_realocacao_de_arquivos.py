import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time
from selenium.webdriver.common.keys import Keys
import time as time
import datetime
from datetime import datetime, timedelta
import os
import shutil
import pandas as pd


presentday = datetime.now()
yesterday = presentday - timedelta(1)
last_week = presentday - timedelta(7)

navegador = webdriver.Chrome()
navegador.maximize_window()

navegador.get("https://degustone.com.br/login")

# Inserindo o documento
documento_input = WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@name='documento']")))
documento_input.send_keys("06266555794")
time.sleep(6)
button = WebDriverWait(navegador, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//button[./span[contains(text(),'{1º digito da senha}')]]"))
)
button.click()

button = WebDriverWait(navegador, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//button[./span[contains(text(),{2º digito da senha})]]"))
)
button.click()

button = WebDriverWait(navegador, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//button[./span[contains(text(),{3º digito da senha})]]"))
)
button.click()

button = WebDriverWait(navegador, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//button[./span[contains(text(),{4º digito da senha})]]"))
)
button.click()

button = WebDriverWait(navegador, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//button[./span[contains(text(),{5º digito da senha})]]"))
)
button.click()

button = WebDriverWait(navegador, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//button[./span[contains(text(),{6º digito da senha})]]"))
)

button.click()

time.sleep(2)

navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/form[1]/div[3]/div[1]/button[1]').click()
time.sleep(2)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[2]/span[1]/div[1]/div[1]/div[1]/span[1]/button[1]').click()
time.sleep(5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/form[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span[1]/div[1]/div[1]/div[1]/span[1]/input[1]').click()
time.sleep(0.5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/form[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span[1]/div[1]/div[1]/div[1]/span[1]/input[1]').clear()
time.sleep(0.5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/form[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span[1]/div[1]/div[1]/div[1]/span[1]/input[1]').send_keys("1")
time.sleep(0.5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/form[1]/div[1]/div[2]/div[1]/div[2]/div[1]/span[1]/div[1]/div[1]/div[1]/span[1]/input[1]').click()
time.sleep(0.5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/form[1]/div[1]/div[2]/div[1]/div[2]/div[1]/span[1]/div[1]/div[1]/div[1]/span[1]/input[1]').clear()
time.sleep(0.5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/form[1]/div[1]/div[2]/div[1]/div[2]/div[1]/span[1]/div[1]/div[1]/div[1]/span[1]/input[1]').send_keys("3078")
time.sleep(0.5)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/ul[1]/li[1]/span[1]/div[1]/button[2]').click()
time.sleep(10)
navegador.find_element(By.XPATH, "(//ul[@role='menu'])[1]").click()
time.sleep(2)
navegador.find_element(By.XPATH, "(//input[@placeholder='Pesquisar por'])[1]").send_keys("{nome do menu desejado}")
time.sleep(1)
time.sleep(0.5)
navegador.find_element(By.XPATH, "(//a[normalize-space()='{nome do menu desejado}'])[1]").click()
time.sleep(3)
navegador.find_element(By.XPATH, "//input[@placeholder='Data Inicial']").click()
time.sleep(0.5)
navegador.find_element(By.XPATH, "(//span[normalize-space()='Último mês'])[1]").click()

folder = "C:\\Users\\{seu usuário}\\Downloads"
destination_folder = "{caminho da pasta desejada}"

navegador.find_element(By.XPATH, "(//div[@class='multiselect__tags'])[2]").click()
time.sleep(1)
navegador.find_element(By.XPATH, "(//input[@placeholder='Selecione uma Loja'])[1]").send_keys({nome da loja})
time.sleep(0.5)
navegador.find_element(By.XPATH, "(//input[@placeholder='Selecione uma Loja'])[1]").send_keys(Keys.ENTER)
time.sleep(2)
navegador.find_element(By.XPATH, "(//button[@type='submit'])[1]").click()
time.sleep(2)
navegador.switch_to.window(navegador.window_handles[1])
time.sleep(1)
navegador.find_element(By.XPATH, '/html[1]/body[1]/div[1]/table[1]/tbody[1]/tr[1]/td[3]/button[3]').click()
time.sleep(1)
navegador.close()
navegador.switch_to.window(navegador.window_handles[0])
time.sleep(5)

filename = max([os.path.join(folder, f) for f in os.listdir(folder)], key=os.path.getctime)
{var(nome da sua preferencia)} = shutil.move(filename,os.path.join(folder, f"{yesterday.strftime('%Y%m')}-{nome da loja}.html"))
destination_path = os.path.join(destination_folder, f"{yesterday.strftime('%Y%m')}-{nome da loja}.html")

shutil.move({var(nome da sua preferencia)}, destination_path)
print({var(nome da sua preferencia)})
