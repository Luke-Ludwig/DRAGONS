from abc import ABC, abstractmethod

from bokeh.layouts import row
from bokeh.models import Slider, TextInput, ColumnDataSource, BoxAnnotation, Button, CustomJS

from geminidr.interactive import server


class PrimitiveVisualizer(ABC):
    def __init__(self):
        self.submit_button = Button(label="Submit")
        self.submit_button.on_click(self.submit_button_handler)
        callback = CustomJS(code="""
            window.close();
        """)
        self.submit_button.js_on_click(callback)

    def submit_button_handler(self, stuff):
        """
        Handle the submit button by stopping the bokeh server, which
        will resume python execution in the DRAGONS primitive.

        Parameters
        ----------
        stuff
            passed by bokeh, but we do not use it

        Returns
        -------
        none
        """
        server.bokeh_server.io_loop.stop()

    def visualize(self, doc):
        """
        Perform the visualization.

        This is called via bkapp by the bokeh server and happens
        when the bokeh server is spun up to interact with the user.

        Subclasses should implement this method with their particular
        UI needs, but also should call super().visualize(doc) to
        listen for session terminations.

        Returns
        -------
        none
        """
        doc.on_session_destroyed(self.submit_button_handler)

    def make_slider_for(self, title, value, step, min_value, max_value, handler):
        """
        Make a slider widget to use in the bokeh interface.

        This method handles some extra boilerplate logic for inspecting
        our primitive field configurations and determining sensible values
        for minimum, maximum, etc.

        Parameters
        ----------
        title : str
            Title for the slider
        value : int
            Value to initially set
        step : int
            Step size
        min_value : int
            Minimum slider value, or None defaults to min(value,0)
        max_value : int
            Maximum slider value, or None defaults to value*2
        handler : method
            Function to handle callbacks when value of the slider changes

        Returns
        -------
            :class:`bokeh.models.Slider` slider widget for bokeh interface
        """
        start = min(value, min_value) if min_value else min(value, 0)
        end = max(value, max_value) if max_value else max(10, value*2)
        slider = Slider(start=start, end=end, value=value, step=step, title=title)
        slider.width = 256

        text_input = TextInput()
        text_input.width = 64
        text_input.value = str(value)
        component = row(slider, text_input)

        def update_slider(attr, old, new):
            if old != new:
                ival = int(new)
                if ival > slider.end and not max_value:
                    slider.end = ival
                if 0 <= ival < slider.start and min_value is None:
                    slider.start = ival
                if slider.start <= ival <= slider.end:
                    slider.value = ival

        def update_text_input(attr, old, new):
            if new != old:
                text_input.value = str(new)

        slider.on_change("value", update_text_input, handler)
        text_input.on_change("value", update_slider)
        return component


class GIControlListener(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def giupdate(self, data):
        pass


class GICoordsSource:
    def __init__(self):
        self.listeners = list()

    def add_gilistener(self, coords_listener):
        if not isinstance(coords_listener, GICoordsListener):
            raise ValueError("Must pass a GICoordsListener implementation")
        self.listeners.append(coords_listener)

    def ginotify(self, x_coords, y_coords):
        for l in self.listeners:
            l.giupdate(x_coords, y_coords)


class GICoordsListener(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def giupdate(self, x_coords, y_coords):
        pass


class GIScatter(GICoordsListener):
    def __init__(self, fig, x_coords=None, y_coords=None, color="blue", radius=5):
        if x_coords is None:
            x_coords = []
        if y_coords is None:
            y_coords = []
        self.source = ColumnDataSource({'x': x_coords, 'y': y_coords})
        self.scatter = fig.scatter(x='x', y='y', source=self.source, color=color, radius=radius)

    def giupdate(self, x_coords, y_coords):
        self.source.data = {'x': x_coords, 'y': y_coords}

    def clear_selection(self):
        self.source.selected.update(indices=[])


class GILine(GICoordsListener):
    def __init__(self, fig, x_coords=[], y_coords=[], color="red"):
        if x_coords is None:
            x_coords = []
        if y_coords is None:
            y_coords = []
        self.line_source = ColumnDataSource({'x': x_coords, 'y': y_coords})
        self.line = fig.line(x='x', y='y', source=self.line_source, color=color)

    def giupdate(self, x_coords, y_coords):
        self.line_source.data = {'x': x_coords, 'y': y_coords}


class BandListener(ABC):
    @abstractmethod
    def adjust_band(self, band_id, start, stop):
        pass

    def delete_band(self, band_id):
        pass


class BandModel(object):
    def __init__(self):
        self.band_id = 1
        self.listeners = list()

    def add_listener(self, listener):
        if not isinstance(listener, BandListener):
            raise ValueError("must be a BandListener")
        self.listeners.append(listener)

    def adjust_band(self, band_id, start, stop):
        for listener in self.listeners:
            listener.adjust_band(band_id, start, stop)


class GIBands(BandListener):
    def __init__(self, fig, model):
        self.model = model
        model.add_listener(self)
        self.bands = dict()
        self.fig = fig

    def adjust_band(self, band_id, start, stop):
        if band_id in self.bands:
            band = self.bands[band_id]
            band.left = start
            band.right = stop
        else:
            band = BoxAnnotation(left=start, right=stop, fill_alpha=0.1, fill_color='navy')
            self.fig.add_layout(band)
            self.bands[band_id] = band

    def delete_band(self, band_id):
        if band_id in self.bands:
            band = self.bands[band_id]
            # TODO remove it


class ApertureModel(object):
    def __init__(self):
        self.start = 100
        self.end = 300
        self.aperture_id = 1
        self.listeners = list()

    def add_listener(self, listener):
        self.listeners.append(listener)

    def adjust_aperture(self, aperture_id, start, end):
        for l in self.listeners:
            l.handle_aperture(aperture_id, start, end)


class ApertureView(object):
    def __init__(self, model, figure, y):
        self.boxes = dict()

        # left, right bars - line between - label aperture #
        ## This really isn't great.  Maybe with some work in creating a pixel-based glass pane overlay
        ## of some sort, if there even is a Bokeh equivalent.  For now, stubbing out to Box
        # self.label = Label(x=(model.start+model.end)/2-5, y=y+10, text="%s" % model.aperture_id)
        # figure.add_layout(self.label)
        # self.left_source = ColumnDataSource({'x': [model.start, model.start], 'y': [y-20, y+20]})
        # self.left = figure.line(x='x', y='y', source=self.left_source, color="purple")
        # self.right_source = ColumnDataSource({'x': [model.end, model.end], 'y': [y-20, y+20]})
        # self.right = figure.line(x='x', y='y', source=self.right_source, color="purple")
        # self.line_source = ColumnDataSource({'x': [model.start, model.end], 'y': [y, y]})
        # self.line = figure.line(x='x', y='y', source=self.line_source, color="purple")

        self.figure = figure
        model.add_listener(self)

    def handle_aperture(self, aperture_id, start, end):
        if aperture_id in self.boxes:
            box = self.boxes[aperture_id]
            box.left = start
            box.right = end
        else:
            box = BoxAnnotation(left=start, right=end, fill_alpha=0.1, fill_color='green')
            self.boxes[aperture_id] = box
            self.figure.add_layout(box)
