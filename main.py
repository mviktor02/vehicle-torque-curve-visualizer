from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.slider import Slider
from kivymd.app import MDApp
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import json
from kivy.core.window import Window

Window.size = (600, 600)


class Manager(ScreenManager):
    pass


class MenuScreen(Screen):
    def choose_file_screen(self):
        self.manager.current = "choose_file_screen"


class ChooseFileScreen(Screen):
    def test_button(self, selection):
        self.ids.load_button.disabled = not self.can_load(selection)

    @staticmethod
    def can_load(selection):
        if len(selection) == 1 and selection[0].endswith(".json"):
            with open(selection[0]) as f:
                json_dict = json.load(f)
                if 'torque_curve' in json_dict:
                    return True
                else:
                    return False
        else:
            return False

    def load(self, selection):
        if self.can_load(selection):
            self.manager.get_screen("graphs_screen").load(selection[0])
            self.manager.current = "graphs_screen"


class GearRatioPopup(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.pos_hint = {'x': 0, 'y': 0}
        self.gear_labels = []
        self.diff_label = None

    def load_gear_ratios(self, gear_ratios, diff):
        # reset widget
        self.clear_widgets()
        self.gear_labels = []
        self.diff_label = None
        self.rows = len(gear_ratios)+1
        # add differential slider and label
        diff_slider = Slider()
        diff_slider.min = 0.10
        diff_slider.max = 10.0
        diff_slider.step = 0.01
        diff_slider.orientation = 'horizontal'
        diff_slider.bind(value=lambda instance, val: self.tweak_diff(val))
        diff_slider.size_hint_x = .8
        self.diff_label = Label()
        self.diff_label.size_hint_x = .2
        self.add_widget(self.diff_label)
        self.add_widget(diff_slider)
        diff_slider.value = diff
        # add a slider and label for each gear
        for i in range(len(gear_ratios)):
            slider = Slider()
            slider.min = 0.10
            slider.max = 10.0
            slider.step = 0.01
            slider.orientation = 'horizontal'
            slider.bind(value=lambda instance, val, j=i: self.tweak_gear(j, val))
            slider.size_hint_x = .8
            gear_label = Label()
            gear_label.size_hint_x = .2
            self.gear_labels.append(gear_label)
            self.add_widget(gear_label)
            self.add_widget(slider)
            slider.value = gear_ratios[i]

    def tweak_gear(self, gear, value):
        graphs_screen = App.get_running_app().root.get_screen('graphs_screen')
        self.gear_labels[gear].text = str(gear+1) + ': ' + str(round(value, 2))
        graphs_screen.gear_ratios[gear] = round(value, 2)
        graphs_screen.update_gear_graph()

    def tweak_diff(self, value):
        graphs_screen = App.get_running_app().root.get_screen('graphs_screen')
        self.diff_label.text = 'Diff: ' + str(round(value, 2))
        graphs_screen.differential = round(value, 2)
        graphs_screen.update_gear_graph()


class GraphsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.has_hp_graph = False
        self.has_gear_graph = False
        self.rpm = []
        self.vehicle_dict = None
        self.torque = []
        self.gear_ratios = []
        self.differential = []

    def init_variables(self):
        plt.close('all')
        self.rpm = []
        self.vehicle_dict = None
        self.torque = []
        self.gear_ratios = []
        self.differential = []

    def load(self, file):
        self.init_variables()
        # Read input data
        with open(file) as f:
            self.vehicle_dict = json.load(f)
            self.torque = self.vehicle_dict['torque_curve']
        if 'gear_ratios' in self.vehicle_dict and 'differential_ratio' in self.vehicle_dict:
            self.gear_ratios = self.vehicle_dict['gear_ratios']
            self.differential = self.vehicle_dict['differential_ratio']

        self.update_horsepower_graph()

        if self.gear_ratios and self.differential:  # only create gear ratio graph if our file contains the necessary keys
            Window.size = (1200, 600)
            self.update_gear_graph()
            if not self.has_gear_graph:
                wheel_trq_box = self.ids.wheel_torque
                wheel_trq_box.size_hint_x = .5
                torque_box = self.ids.torque_and_hp
                torque_box.size_hint_x = .5
                wheel_trq_box.add_widget(FigureCanvasKivyAgg(plt.gcf()))
                self.ids.tweak_gears_btn.opacity = 1
                self.ids.tweak_gears_btn.disabled = False
                self.ids.export_gears_btn.disabled = False
                self.has_gear_graph = True
        elif self.has_gear_graph:
            Window.size = (600, 600)
            self.ids.wheel_torque.clear_widgets()
            self.ids.torque_and_hp.size_hint_x = 1
            self.ids.tweak_gears_btn.opacity = 0
            self.ids.tweak_gears_btn.disabled = True
            self.ids.export_gears_btn.disabled = True
            self.has_gear_graph = False

    def open_tweak_gears_popup(self):
        gear_ratio_popup = GearRatioPopup()
        gear_ratio_popup.load_gear_ratios(self.gear_ratios, self.differential)
        popup = Popup(title="Tweak Gear Ratios", content=gear_ratio_popup, size_hint=(.5, .85),
                      pos_hint={"top": .95, "x": 0})
        popup.open()

    def export_as(self, fig):
        name = self.ids.namer.text
        if name and (fig == 0 or fig == 1):
            plt.figure(fig)
            plt.savefig(name)
            popup = Popup(title="Successfully exported "+name, content=BoxLayout(), size_hint=(.4, .2))
            popup.open()

    def update_horsepower_graph(self):
        plt.figure(0)
        plt.cla()
        box = self.ids.torque_and_hp
        box.clear_widgets()
        horsepower = []
        for idx, trq in enumerate(self.torque):
            newrpm = 1000 + idx * 100
            self.rpm.append(newrpm)
            current_torque = trq / 1.356
            horsepower.append(round(current_torque * newrpm / 5252, 1))

        plt.plot(self.rpm, self.torque, label='Torque (Nm)')
        plt.plot(self.rpm, horsepower, label='Horsepower')
        plt.legend()
        plt.grid()
        plt.title("Torque and HP curves")
        plt.ylabel("Torque (Nm) / Horsepower")
        plt.xlabel("RPM")
        box.add_widget(FigureCanvasKivyAgg(plt.gcf()))

    def update_gear_graph(self):
        plt.figure(1)
        plt.cla()
        box = self.ids.wheel_torque
        box.clear_widgets()
        for i in range(len(self.gear_ratios)):
            gear = []
            for j in range(len(self.torque)):
                gear.append(self.gear_ratios[i] * self.differential * self.torque[j])
            plt.plot(self.rpm, gear, label=('gear ' + str(i + 1)))
        plt.legend()
        plt.grid()
        plt.title("Wheel Torque Curves per Gear")
        plt.ylabel("Wheel Torque (Nm)")
        plt.xlabel("RPM")
        if self.has_gear_graph:
            box.add_widget(FigureCanvasKivyAgg(plt.gcf()))


class MainApp(MDApp):
    def build(self):
        self.title = "Torque Curve Visualizer"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        Builder.load_file('vehicle-torque-curves.kv')
        return Manager()


MainApp().run()
