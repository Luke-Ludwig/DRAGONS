import numpy as np
from bokeh.layouts import row, column
from bokeh.models import Column, Div, Button

from geminidr.interactive import server, interactive
from geminidr.interactive.interactive import GICoordsSource, GILine, GIScatter, GIFigure, GISlider, _dequantity, \
    GIMaskedSigmadCoords
from gempy.library import astromodels


__all__ = ["interactive_spline", ]


class SplineModel:
    def __init__(self, ext, coords, weights, order, niter, grow):
        self.ext = ext
        self.coords = coords
        self.weights = weights
        self.order = order
        self.niter = niter
        self.grow = grow

        # These are the heart of the model.  The users of the model
        # register to listen to these two coordinate sets to get updates.
        # Whenever there is a call to recalc_spline, these coordinate
        # sets will update and will notify all registered listeners.
        self.mask_points = GICoordsSource()
        self.fit_line = GICoordsSource()

        self.spline = None

        self.coords.add_mask_listener(self.update_coords)

    def update_coords(self, x, y):
        self.recalc_spline()

    def recalc_spline(self):
        """
        Recalculate the spline based on the currently set parameters.

        Whenever one of the parameters that goes into the spline function is
        changed, we come back in here to do the recalculation.  Additionally,
        the resulting spline is used to update the line and the masked underlying
        scatter plot.

        Returns
        -------
        none
        """
        x, y = self.coords.x_coords[self.coords.mask], self.coords.y_coords[self.coords.mask]

        # zpt_err = self.zpt_err
        weights = self.weights
        order = self.order
        niter = self.niter
        grow = self.grow
        ext = self.ext

        self.spline = astromodels.UnivariateSplineWithOutlierRemoval(x, y,
                                                                     w=weights[self.coords.mask],  # w=1. / zpt_err.value,
                                                                     order=order,
                                                                     niter=niter,
                                                                     grow=grow)

        splinex = np.linspace(min(x), max(x), ext.shape[0])

        self.mask_points.notify_coord_listeners(x[self.spline.mask], y[self.spline.mask])
        self.fit_line.notify_coord_listeners(splinex, self.spline(splinex))


class SplineVisualizer(interactive.PrimitiveVisualizer):
    def __init__(self, ext, coords, weights, order, niter, grow, min_order, max_order,
                 min_niter, max_niter, min_grow, max_grow,
                 x_axis_label, y_axis_label):
        """
        Create a spline visualizer.

        This makes a visualizer for letting a user interactively set the
        spline parameters.  The class handles some common logic for setting up
        the web document and for holding the result of the interaction.  In
        future, other visualizers will follow a similar pattern.

        Parameters
        ----------
        ext :
            Astrodata extension to visualize spline for
        coords : `~MaskedSigmadCoords`
            coordinates
        weights :
            weights
        order : int
            order to initially use for the visualization (this may be adjusted interactively)
        niter : int
            iterations to perform in doing the spline (this may be adjusted interactively)
        grow : int
            how far out to extend rejection (this may be adjusted interactively)
        min_order : int
            minimum value for order in UI
        max_order : int
            maximum value for order in UI
        min_niter : int
            minimum value for niter in UI
        max_niter : int
            maximum value for niter in UI
        min_grow : int
            minimum value for grow in UI
        max_grow : int
            maximum value for grow in UI
        """
        super().__init__()
        # Note that self._fields in the base class is setup with a dictionary mapping conveniently
        # from field name to the underlying config.Field entry, even though fields just comes in as
        # an iterable
        self.model = SplineModel(ext, coords, weights, order, niter, grow)
        self.p = None
        self.spline = None
        self.scatter = None
        self.scatter_touch = None
        self.line = None
        self.scatter_source = None
        self.line_source = None
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label

        self.min_order = min_order
        self.max_order = max_order
        self.min_niter = min_niter
        self.max_niter = max_niter
        self.min_grow = min_grow
        self.max_grow = max_grow

    def mask_button_handler(self):
        indices = self.scatter_touch.source.selected.indices
        self.scatter_touch.clear_selection() # source.selected.indices.clear()
        self.scatter.clear_selection() # source.selected.indices.clear()
        self.model.coords.addmask(indices)

    def unmask_button_handler(self):
        indices = self.scatter_touch.source.selected.indices
        self.scatter_touch.clear_selection() # source.selected.indices.clear()
        self.scatter.clear_selection() # source.selected.indices.clear()
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

        x = self.model.coords.x_coords
        y = self.model.coords.y_coords
        order = self.model.order
        niter = self.model.niter
        grow = self.model.grow

        order_slider = GISlider("Order", order, 1, self.min_order, self.max_order,
                                self.model, "order", self.model.recalc_spline)
        niter_slider = GISlider("Num Iterations", niter, 1,  self.min_niter, self.max_niter,
                                self.model, "niter", self.model.recalc_spline)
        grow_slider = GISlider("Grow", grow, 1, self.min_grow, self.max_grow,
                               self.model, "grow", self.model.recalc_spline)
        mask_button = Button(label="Mask")
        mask_button.on_click(self.mask_button_handler)

        unmask_button = Button(label="Unmask")
        unmask_button.on_click(self.unmask_button_handler)

        # Create a blank figure with labels
        self.p = GIFigure(plot_width=600, plot_height=500,
                          title='Interactive Spline',
                          tools="pan,wheel_zoom,box_zoom,reset,lasso_select,box_select,tap",
                          x_axis_label=self.x_axis_label, y_axis_label=self.y_axis_label)

        # We can plot this here because it never changes
        # the overlay we plot later since it does change, giving
        # the illusion of "coloring" these points
        self.scatter_touch = GIScatter(self.p, x, y, color="blue", radius=5)

        self.scatter = GIScatter(self.p, color="black")
        self.model.coords.add_mask_listener(self.scatter.update_coords)

        self.line = GILine(self.p)
        self.model.fit_line.add_coord_listener(self.line.update_coords)

        controls = Column(order_slider.component, niter_slider.component, grow_slider.component,
                          mask_button, unmask_button, self.submit_button)

        self.details = Div(text="")
        self.model.fit_line.add_coord_listener(self.update_details)
        self.model.recalc_spline()

        col = column(self.p.figure, self.details)
        layout = row(controls, col)

        doc.add_root(layout)

    def update_details(self, x, y):
        order = self.model.order
        self.details.text = \
        """
        <b>Type of Function:</b> ?<br/>
        <b>Order:</b> %s<br/>
        <b>Rejection Method:</b> ?<br/>
        <b>Rejection Low:</b> ? <br/>
        <b>Rejection High:</b> ?<br/>
        <b>Number of Iterations:</b> %s<br/>
        <b>Grow:</b> %s<br/>
        <b>RMS: ?<br/>
        <b>RMS Units:</b> (presumably annotate RMS with this)<br/> 
        """ \
         % (order, self.model.niter, self.model.grow)

    def result(self):
        """
        Get the result of the user interaction.

        Returns
        -------
        :class:`astromodels.UnivariateSplineWithOutlierRemoval`
        """
        return self.model.spline


def interactive_spline(ext, wave, zpt, weights, order, niter, grow, min_order, max_order, min_niter, max_niter,
                       min_grow, max_grow, x_axis_label="X", y_axis_label="Y"):
    """
    Build a spline via user interaction.

    This method spins up bokeh and uses a web-based bokeh gui to create a spline
    from user input.  Values passed in are used for the data points and as a
    starting point for the interface.

    Parameters
    ----------
    ext
        FITS extension from astrodata
    wave
    zpt
    weights
    order
        order for the spline calculation
    niter
        number of iterations for the spline calculation
    grow
        grow for the spline calculation
    min_order : int
        minimum value for order in UI
    max_order : int
        maximum value for order in UI
    min_niter : int
        minimum value for niter in UI
    max_niter : int
        maximum value for niter in UI
    min_grow : int
        minimum value for grow in UI
    max_grow : int
        maximum value for grow in UI

    Returns
    -------
    :class:`astromodels.UnivariateSplineWithOutlierRemoval`
    """
    ndx, ndy = _dequantity(wave, zpt)
    masked_coords = GIMaskedSigmadCoords(ndx, ndy)
    spline = SplineVisualizer(ext, masked_coords, weights, order, niter, grow, min_order, max_order,
                              min_niter, max_niter, min_grow, max_grow, x_axis_label=x_axis_label,
                              y_axis_label=y_axis_label)
    server.set_visualizer(spline)

    server.start_server()

    return spline.result()
