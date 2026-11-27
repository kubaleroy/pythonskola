# Textova hra
#
#
#
#Lokace: 
#
#
#
#
#
#
import customtkinter as ctk
import ctypes
from resources import tiles 
from PIL import Image

res = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)

#build screen
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hra")
        self.resscale = 0.5
        self.size = [int(res[0]*self.resscale),int(res[1]*self.resscale)]
        self.geometry(f"{int(res[0]*self.resscale)}x{int(res[1]*self.resscale)}")
        self.sizelabel = ctk.CTkLabel(self, text="test", font=ctk.CTkFont(size=18))
        self.sizelabel.grid(row=0, column=0, padx=20, pady=20)

    def get_size(self, event):
        if event.widget is self:
            self.help_size == self.geometry().split("+")[0].split
            self.size = [int(self.help_size.split("x")[0]),int(self.help_size.split("x")[1])]
            self.sizelabel.configure(text=f"Wsize: {self.size}")

                         
tiles.getRandomFloorTile().show()
app = App()
#app.mainloop()