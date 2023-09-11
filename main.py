import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
import sqlite3
import requests
import spacy

github_db_url = "https://github.com/tilin2009/conocimientoonline.json/raw/main/conocimiento.db"

conn = sqlite3.connect('conocimiento.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS conocimiento
                (pregunta TEXT PRIMARY KEY, respuesta TEXT)''')
conn.commit()

nlp = spacy.load("es_core_news_sm")

class FazuInfoApp(App):
    def build(self):
        self.conocimiento = {}

        layout = FloatLayout(size=(400, 600))

        chat_box = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 0.85))

        self.chat_label = Label(text="¡Bienvenido! Haz una pregunta. Para más información, escribe 'Quiero información'.")
        chat_box.add_widget(self.chat_label)

        self.chat_history = ScrollView(size_hint=(1, 1))
        self.chat_messages = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.chat_messages.bind(minimum_height=self.chat_messages.setter('height'))
        self.chat_history.add_widget(self.chat_messages)
        chat_box.add_widget(self.chat_history)

        self.input_box = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.15))
        self.pregunta_input = TextInput(hint_text="Escribe aquí tu pregunta recuerda si no es una operación empieza con '/'")
        self.input_box.add_widget(self.pregunta_input)

        buscar_button = Button(text="Enviar", size_hint=(0.2, 1))
        buscar_button.bind(on_press=self.buscar_respuesta)
        self.input_box.add_widget(buscar_button)

        chat_box.add_widget(self.input_box)
        layout.add_widget(chat_box)

        return layout

    def cargar_conocimiento_publico(self):
        if self.hay_actualizacion_en_github():
            self.actualizar_desde_github()
        self.conocimiento = self.cargar_conocimiento_desde_sqlite('conocimiento_publico')

    def hay_actualizacion_en_github(self):
        try:
            response = requests.head(github_db_url)
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    def actualizar_desde_github(self):
        try:
            response = requests.get(github_db_url)
            if response.status_code == 200:
                with open('conocimiento.db', 'wb') as db_file:
                    db_file.write(response.content)
                print("Base de datos actualizada desde GitHub.")
        except requests.ConnectionError:
            print("No se pudo conectar a GitHub para actualizar la base de datos.")

    def cargar_conocimiento_desde_sqlite(self, nodo):
        try:
            cursor.execute("SELECT respuesta FROM conocimiento WHERE pregunta = ?", (nodo,))
            data = cursor.fetchone()
            if data:
                return {nodo: data[0]}
            else:
                print(f"La pregunta '{nodo}' no existe en la base de datos.")
                return {}
        except Exception as e:
            print(f"Error al cargar datos desde SQLite: {e}")
            return {}

    def mostrar_popup_cargado(self):
        popup = Popup(title='Conocimiento Cargado', content=Label(text='Conocimiento cargado correctamente'), size_hint=(None, None), size=(300, 200))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

    def buscar_respuesta(self, instance):
        pregunta = self.pregunta_input.text.lower()

        if pregunta.lower() == 'quiero información':
            self.mostrar_respuesta("¡Bienvenido! Haz una pregunta. Para más información, escribe 'infok'.")
            return

        if re.match(r"^(calcula|calcular)?\s*(.*)$", pregunta):
            expresion = re.sub(r"^(calcula|calcular)?\s*", "", pregunta)
            try:
                resultado = eval(expresion)
                self.mostrar_respuesta(f"El resultado es: {resultado}")
                return
            except Exception as e:
                pass

        if "aplica la fórmula de arquímedes" in pregunta:
            formula_arquimedes = "Fuerza de flotación = Densidad del fluido * Volumen del objeto * Gravedad"
            self.mostrar_respuesta(formula_arquimedes)
            return

        if pregunta.startswith("busca sobre "):
            entidad = pregunta.replace("busca sobre ", "")
            respuesta = self.buscar_informacion_sobre_entidad(entidad)
            if respuesta:
                self.mostrar_respuesta(respuesta)
            else:
                self.mostrar_respuesta(f"No encontré información sobre {entidad}.")
            return

        if pregunta.startswith("determina la oxidación de "):
            formula = pregunta.replace("determina la oxidación de ", "")
            respuesta = self.determinar_oxidacion(formula)
            self.mostrar_respuesta(respuesta)
            return

        if "principio de bernoulli" in pregunta:
            respuesta, formula = self.resolver_problema_bernulli(pregunta)
            self.mostrar_respuesta_larga(respuesta, formula)
        elif pregunta in self.conocimiento:
            respuesta = self.conocimiento[pregunta]
            self.mostrar_respuesta(respuesta)
        else:
            self.mostrar_cuadro_respuesta_pendiente(pregunta)

    def mostrar_respuesta(self, respuesta):
        mensaje = Label(text=respuesta, halign="left", valign="top", size_hint_y=None)
        mensaje.bind(size=mensaje.setter('text_size'))
        self.chat_messages.add_widget(mensaje)
        self.pregunta_input.text = ""
        self.chat_history.scroll_to(mensaje)

    def mostrar_respuesta_larga(self, respuesta, formula):
        mensaje_respuesta = Label(text=respuesta, halign="left", valign="top", size_hint_y=None)
        mensaje_respuesta.bind(size=mensaje_respuesta.setter('text_size'))

        mensaje_formula = Label(text=formula, halign="left", valign="top", size_hint_y=None)
        mensaje_formula.bind(size=mensaje_formula.setter('text_size'))

        self.chat_messages.add_widget(mensaje_respuesta)
        self.chat_messages.add_widget(mensaje_formula)

        self.pregunta_input.text = ""
        self.chat_history.scroll_to(mensaje_formula)

    def mostrar_cuadro_respuesta_pendiente(self, pregunta):
        content = BoxLayout(orientation='vertical')
        respuesta_input = TextInput(hint_text="Escribe aquí la respuesta")
        content.add_widget(respuesta_input)

        popup = Popup(title='Agregar Respuesta', content=content, size_hint=(None, None), size=(400, 200))
        content.add_widget(Button(text='Guardar', on_press=lambda x: self.guardar_respuesta_popup(popup, pregunta, respuesta_input.text)))
        popup.open()

    def guardar_respuesta_popup(self, popup, pregunta, respuesta):
        if respuesta:
            self.conocimiento[pregunta] = respuesta
            cursor.execute("INSERT OR REPLACE INTO conocimiento (pregunta, respuesta) VALUES (?, ?)", (pregunta, respuesta))
            conn.commit()
            self.mostrar_respuesta(respuesta)
            popup.dismiss()
        else:
            popup.dismiss()

    def buscar_informacion_sobre_entidad(self, entidad):
        respuestas = [respuesta for pregunta, respuesta in self.conocimiento.items() if entidad.lower() in pregunta.lower()]
        if respuestas:
            respuesta_completa = " ".join(respuestas)
            return respuesta_completa
        return None

    def determinar_oxidacion(self, formula):
        try:
            substance = Substance.from_formula(formula)
            oxidation_states = substance.oxidation_states
            return f"Oxidación de {formula}: {oxidation_states}"
        except Exception as e:
            return f"No se pudo determinar la oxidación de {formula}."

    def resolver_problema_bernulli(self, pregunta):
        p1 = 6000
        v1 = 3
        v2 = 2
        h1 = 8
        h2 = 8
        g = 9.81
        p = 1000

        p2 = p1 + 0.5 * p * (v1 ** 2 - v2 ** 2) + p * g * (h1 - h2)
        formula = f"{p1} + 0.5 * {p} * ({v1}^2 - {v2}^2) + {p} * {g} * ({h1} - {h2})"
        return f"El resultado es: {p2}", formula

if __name__ == '__main__':
    app = FazuInfoApp()
    app.cargar_conocimiento_publico()
    app.run()
