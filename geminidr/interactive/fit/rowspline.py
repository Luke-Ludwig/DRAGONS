
from bokeh.layouts import column, row
from bokeh.models import Tabs, Panel, ColumnDataSource, Button, Div
from bokeh.plotting import figure

from gempy.library import astromodels

from geminidr.interactive import interactive


class RowSplineTab:
    def __init__(self, view, shape, pixels, masked_data, order, weights, grow=0, recalc_button=False,
                 **spline_kwargs):
        if isinstance(masked_data, list) and len(masked_data[0]) > 1:
            # multiplot, no select tools
            tools = "pan,wheel_zoom,box_zoom,reset"
        else:
            tools = "pan,wheel_zoom,box_zoom,reset,lasso_select,box_select,tap"
            masked_data = [masked_data]

        self.view = view
        self.recalc_button = recalc_button
        self.pixels = pixels
        self.masked_data = masked_data
        self.order = order
        self.grow=grow
        self.weights = weights
        self.spline_kwargs = spline_kwargs
        # self.model = SplineModel(shape, pixels, masked_data, weights, self.order, 1, 1)  #order, niter, grow)
        # Create a blank figure with labels
        self.p = figure(plot_width=600, plot_height=500,
                        title='Interactive Spline',
                        tools=tools,
                        x_axis_label='x', y_axis_label='y')

        self.row = 0

        colors = ['red','blue','orange','green','purple','yellow']
        md = masked_data[self.row]
        # only do some of the lines to give a sense of it - if we did them all the ui falls over
        self.scatter_source = ColumnDataSource({'x': pixels, 'y': md})
        self.scatter = self.p.scatter(x='x', y='y', source=self.scatter_source, color="black", radius=5)
        # we'll add data to the line sources whenever a fit is recalculated
        self.line_source = ColumnDataSource({'x': [], 'y': []})
        self.line = self.p.line(x='x', y='y', source=self.line_source, color='blue', level='overlay',
                                line_width=3)

        # Setup Controls
        row_slider = interactive.build_text_slider("Row", self.row, 1, 0, len(masked_data)-1, self, "row",
                                                   self.preview_fit, True, range_expansion=False)
        order_slider = interactive.build_text_slider("Order", self.order, 1, 1, 50,
                                                     self, "order", self.preview_fit)
        grow_slider = interactive.build_text_slider("Growth radius", self.grow, 1, 0, 10,
                                                    self, "grow", self.preview_fit)
        controls = column(row_slider, order_slider, grow_slider)

        # do an initial fit
        self.preview_fit()

        # controls on left, plot on right
        self.component = row(controls, self.p)

    def preview_fit(self):
        self.spline_kwargs['grow'] = self.grow
        md = self.masked_data[self.row]
        w = self.weights[self.row]
        self.scatter_source.data = {'x': self.pixels, 'y': md}

        spline = astromodels.UnivariateSplineWithOutlierRemoval(self.pixels, md,
                                                                order=self.order, w=w,
                                                                **self.spline_kwargs)
        self.line_source.data = {'x': self.pixels, 'y': spline(self.pixels)}

    def fitted_data(self):
        for spline in self.get_splines():
            yield spline(self.pixels)

    def get_splines(self):
        for md, w in zip(self.masked_data, self.weights):
            spline = astromodels.UnivariateSplineWithOutlierRemoval(self.pixels, md, order=self.order, w=w,
                                                                    **self.spline_kwargs)
            yield spline


class RowSplineVisualizer(interactive.PrimitiveVisualizer):
    def __init__(self, all_shapes, all_pixels, all_masked_data, all_orders, all_weights, config, recalc_button=False,
                 **spline_kwargs):
        super().__init__(config=config)

        self.recalc_button = recalc_button
        self.all_shapes = all_shapes
        self.all_pixels = all_pixels
        self.all_masked_data = all_masked_data
        self.all_orders = all_orders
        self.all_weights = all_weights
        self.spline_kwargs = spline_kwargs

        self.spline_tabs = []

    def visualize(self, doc):
        """
        Start the bokeh document using this visualizer.

        This call is responsible for filling in the bokeh document with
        the user interface.

        Parameters
        ----------
        doc : :class:`~bokeh.document.Document`
            bokeh document to draw the UI in
        """
        super().visualize(doc)
        tabs = Tabs()

        idx = 1
        for shape, pixels, masked_data, order, weights in zip(self.all_shapes, self.all_pixels, self.all_masked_data,
                                                              self.all_orders, self.all_weights):
            tab = RowSplineTab(self, shape, pixels, masked_data, order, weights, recalc_button=self.recalc_button,
                            **self.spline_kwargs)
            self.spline_tabs.append(tab)
            panel = Panel(child=tab.component, title='Spline %s' % idx)
            idx = idx+1
            tabs.tabs.append(panel)

        col = column(tabs, self.submit_button)
        col.sizing_mode = 'scale_width'
        layout = col
        doc.add_root(layout)

    def fitted_data(self):
        fd = []
        for st in self.spline_tabs:
            fd.append([fdi for fdi in st.fitted_data()])
        return fd

    def get_splines(self):
        for st in self.spline_tabs:
            for spline in st.get_splines():
                yield spline
