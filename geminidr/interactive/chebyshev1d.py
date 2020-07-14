import numpy as np
from astropy.modeling import models, fitting
from bokeh.layouts import row
from bokeh.models import Button, Column, Panel, Tabs, ColumnDataSource, Div

from geminidr.interactive import server, interactive
from geminidr.interactive.controls import Controller
from geminidr.interactive.interactive import GIScatter, GILine, GICoordsSource, GICoordsListener, \
    GIBandModel, GIApertureModel, GIFigure, GISlider, GIMaskedCoords, \
    GIModelSource, DifferencingModel
from gempy.library import astromodels


__all__ = ["interactive_chebyshev",]


class ChebyshevModel(GICoordsSource, GICoordsListener, GIModelSource):
    def __init__(self, order, location, dispaxis, sigma_clip, coords, spectral_coords, ext):
        super().__init__()
        GIModelSource.__init__(self)
        self.order = order
        self.location = location
        self.dispaxis = dispaxis
        self.sigma_clip = sigma_clip
        self.coords = coords
        self.spectral_coords = spectral_coords
        self.ext = ext
        self.m_final = None
        self.model_dict = None
        self.x = []
        self.y = []

        # do this last since it will trigger an update, which triggers a recalc
        self.coords.add_gilistener(self)

    def update_coords(self, x_coords, y_coords):
        # The masked coordinates changed, so update our copy and recalculate the model
        self.x = x_coords
        self.y = y_coords
        self.recalc_chebyshev()

    def recalc_chebyshev(self):
        """
        Recalculate the Chebyshev1D based on the currently set parameters.

        Whenever one of the parameters that goes into the spline function is
        changed, we come back in here to do the recalculation.  Additionally,
        the resulting spline is used to update the line and the masked underlying
        scatter plot.

        Returns
        -------
        none
        """
        order = self.order
        location = self.location
        dispaxis = self.dispaxis
        sigma_clip = self.sigma_clip
        ext = self.ext

        m_init = models.Chebyshev1D(degree=order, c0=location,
                                    domain=[0, ext.shape[dispaxis] - 1])
        fit_it = fitting.FittingWithOutlierRemoval(fitting.LinearLSQFitter(),
                                                   sigma_clip, sigma=3)
        try:
            x = self.x
            y = self.y
            self.m_final, _ = fit_it(m_init, x, y)
        except (IndexError, np.linalg.linalg.LinAlgError):
            # This hides a multitude of sins, including no points
            # returned by the trace, or insufficient points to
            # constrain the request order of polynomial.
            self.m_final = models.Chebyshev1D(degree=0, c0=location,
                                              domain=[0, ext.shape[dispaxis] - 1])
        self.model_dict = astromodels.chebyshev_to_dict(self.m_final)

        # notify listeners of new x/y plot data based on our model function
        self.ginotify(self.spectral_coords, self.m_final(self.spectral_coords))
        # notify model listeners that our model function has changed
        self.notify_model_listeners()

    def model_calculate(self, x):
        # we need this wrapper since self.m_final changes with each recalc
        return self.m_final(x)


class Chebyshev1DVisualizer(interactive.PrimitiveVisualizer):
    def __init__(self, x, y, model, min_order, max_order):
        """
        Create a chebyshev1D visualizer.

        This makes a visualizer for letting a user interactively set the
        Chebyshev parameters.  The class handles some common logic for setting up
        the web document and for holding the result of the interaction.  In
        future, other visualizers will follow a similar pattern.

        Parameters
        ----------
        """
        super().__init__()

        if not isinstance(model, ChebyshevModel):
            raise ValueError("Chebyshev1DVisualizer requires ChebyshevModel")

        self.x = x
        self.y = y
        self.model = model

        self.min_order = min_order
        self.max_order = max_order

        # Note that self._fields in the base class is setup with a dictionary mapping conveniently
        # from field name to the underlying config.Field entry, even though fields just comes in as
        # an iterable
        self.p = None
        self.spline = None
        self.scatter = None
        self.masked_scatter = None
        self.scatter_touch = None
        self.line = None
        self.scatter_source = None
        self.line_source = None
        self.spectral_coords = None
        self.model_dict = None
        self.m_final = None

        self.scatter2 = None
        self.line2 = None

        self.controls = None

    def mask_button_handler(self, stuff):
        indices = self.scatter.source.selected.indices
        self.scatter.clear_selection() # source.selected.indices.clear()
        self.masked_scatter.clear_selection()
        self.model.coords.addmask(indices)

    def unmask_button_handler(self, stuff):
        indices = self.scatter.source.selected.indices
        self.scatter.clear_selection() # source.selected.indices.clear()
        self.masked_scatter.clear_selection()
        self.model.coords.unmask(indices)

    def visualize(self, doc):
        """
        Build the visualization in bokeh in the given browser document.

        Parameters
        ----------
        doc
            Bokeh provided document to add visual elements to

        Returns
        -------
        none
        """

        super().visualize(doc)

        # Bands and Apertures don't affect anything, but if we pass these to the GIFigure
        # constructor, we'll see the interface in the UI/help text
        # Just sandboxing a basic band UI for the x ranges from Kathleen's demo
        band_model = GIBandModel()
        # Just sandboxing a sample Aperture UI
        aperture_model = GIApertureModel()

        order_slider = GISlider("Order", self.model.order, 1, self.min_order, self.max_order,
                                self.model, "order", self.model.recalc_chebyshev)

        mask_button = Button(label="Mask")
        mask_button.on_click(self.mask_button_handler)

        unmask_button = Button(label="Unmask")
        unmask_button.on_click(self.unmask_button_handler)

        # Add custom tooling
        source = ColumnDataSource(data=dict(x=[], y=[]))

        # Create a blank figure with labels
        p = GIFigure(plot_width=600, plot_height=500,
                     title='Interactive Chebyshev',
                     x_axis_label='X', y_axis_label='Y',
                     tools="pan,wheel_zoom,box_zoom,reset,lasso_select,box_select,tap",
                     band_model=band_model, aperture_model=aperture_model)

        self.p = p

        self.scatter = GIScatter(p, self.x, self.y, color="red", radius=5)
        self.masked_scatter = GIScatter(p, self.x, self.y, color="blue", radius=5)
        self.model.coords.add_gilistener(self.masked_scatter)
        self.line = GILine(p)
        self.model.add_gilistener(self.line)

        # p2 goes in tab 2 and shows the difference between the data y values and the model calculated values
        p2 = GIFigure(plot_width=600, plot_height=500,
                      title='Model Differential',
                      x_axis_label='X', y_axis_label='Y',
                      band_model=band_model, aperture_model=aperture_model)
        self.line2 = GILine(p2)
        differencing_model = DifferencingModel(self.model.coords, self.model, self.model.model_calculate)
        differencing_model.add_gilistener(self.line2)

        # helptext is where the Controller will put help messages for the end user
        # This controls area is a vertical set of UI controls we are placing on the left
        # side of the UI
        helptext = Div(text="")
        self.controls = Column(order_slider.component, self.submit_button, mask_button, unmask_button, helptext)

        # recalculate the chebyshev, causing the data updates to fire and update the UI as well
        self.model.recalc_chebyshev()

        # add the two plots as tabs and place them with controls to the left
        tab1 = Panel(child=p.figure, title="Chebyshev Fit")
        tab2 = Panel(child=p2.figure, title="Chebyshev Differential")
        tabs = Tabs(tabs=[tab1, tab2], name="tabs")
        layout = row(self.controls, tabs)

        # setup controller for key commands
        controller = Controller(self.p, aperture_model, band_model, helptext)

        doc.add_root(layout)


def interactive_chebyshev(ext,  order, location, dispaxis, sigma_clip, in_coords, spectral_coords,
                          min_order, max_order):
    """
    Build a spline via user interaction.

    This method spins up bokeh and uses a web-based bokeh gui to create a spline
    from user input.  Values passed in are used for the data points and as a
    starting point for the interface.

    Parameters
    ----------
    ext
        FITS extension from astrodata
    order
        order for the spline calculation
    location
    dispaxis
    sigma_clip
    in_coords
    spectral_coords
    min_order : int
        minimum value for order slider
    max_order : int
        maximum value for order slider, or None to infer

    Returns
    -------
        dict, :class:`models.Chebyshev1D`
    """
    masked_coords = GIMaskedCoords(in_coords[1-dispaxis], in_coords[dispaxis])
    model = ChebyshevModel(order, location, dispaxis, sigma_clip,
                           masked_coords, spectral_coords, ext)
    server.set_visualizer(Chebyshev1DVisualizer(in_coords[1-dispaxis], in_coords[dispaxis],
                                                model, min_order, max_order))

    server.start_server()

    server.set_visualizer(None)

    return model.model_dict, model.m_final
