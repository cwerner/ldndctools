import folium
import folium.plugins as plugins
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from ldndctools.gui.utils import CONFIG_DEFAULTS, Page
from ldndctools.misc.types import BoundingBox


def bbox_to_bounds(bbox: BoundingBox):
    return (bbox.y1, bbox.x1), (bbox.y2, bbox.x2)


# page elements
# def widget_resolution():
#    pass


def widget_area(self):
    st.sidebar.subheader("② Specify Area")

    sel_region = st.sidebar.multiselect(
        "By region",
        list(self.selector.regions.keys()),
        default=self.state["regions"],
    )
    self.state["regions"] = sel_region

    sel_countries = st.sidebar.multiselect(
        "And/ or by country",
        list(self.selector.countries.keys()),
        default=self.state["countries"],
    )
    self.state["countries"] = sel_countries

    selection = sel_region + sel_countries
    if len(selection) > 0:
        self.selector.set_region(selection)

    with st.sidebar:
        cheatbox = st.expander("Show country codes")
        with cheatbox:
            # hack to left align dataframe columns
            st.markdown(
                """<style>
                    .dataframe {text-align: left !important}
                </style>
                """,
                unsafe_allow_html=True,
            )
            data = pd.DataFrame(self.selector.countries.items())
            data.columns = ["Code", "Name"]
            data = data.set_index("Code")
            st.write(data)


def widget_clip(self):
    st.sidebar.subheader("③ Clip Extent")

    with st.sidebar:
        bbox_widget = st.expander("📦 Bounding Box or 💾 ShapeFile", expanded=False)
        with bbox_widget:
            bbox = self.state["bbox"]

            a1, a2 = st.columns(2)
            a3, a4 = st.columns(2)

            x1 = a1.number_input("x1", min_value=-180, max_value=180, value=bbox.x1)
            x2 = a2.number_input("x2", min_value=-180, max_value=180, value=bbox.x2)
            y1 = a3.number_input("y1", min_value=-90, max_value=90, value=bbox.y1)
            y2 = a4.number_input("y2", min_value=-90, max_value=90, value=bbox.y2)
            self.state["bbox"] = BoundingBox(x1=x1, x2=x2, y1=y1, y2=y2)

            file = st.file_uploader("Drop ShapeFile for custom bbox")  # noqa

        b1, b2 = st.columns(2)
        with b1:
            shrink = st.button("Shrink to extent")
        with b2:
            reset = st.button("Reset to global")

    if shrink:
        extent = self.selector.gdf_mask.bounds.iloc[0]
        new_bbox = BoundingBox(
            x1=np.floor(extent.minx).astype("int").item(),
            x2=np.ceil(extent.maxx).astype("int").item(),
            y1=np.floor(extent.miny).astype("int").item(),
            y2=np.ceil(extent.maxy).astype("int").item(),
        )
        self.state["bbox"] = new_bbox

    if reset:
        self.state["bbox"] = BoundingBox(x1=-180, x2=180, y1=-90, y2=90)


def widget_main(self):
    my_map = create_map(self.selector.gdf_mask, bbox=self.state["bbox"])
    my_map.fit_bounds(bbox_to_bounds(self.state["bbox"]))
    folium_static(my_map)

    selection_widget = st.expander("Currently selected countries", expanded=False)

    with selection_widget:
        st.info(f"{', '.join(sorted(list(self.selector.selected.keys())))}")


def create_map(df, bbox=None):
    m = folium.Map(tiles=None)
    folium.TileLayer("Stamen Toner", name="Stamen Toner", control=False).add_to(m)

    color = "#{:02x}{:02x}{:02x}".format(240, 21, 83)

    # show bbox if it's not the default
    if bbox and bbox != BoundingBox(x1=-180, x2=180, y1=-90, y2=90):
        fg1 = folium.FeatureGroup(name="Bounding box")
        bounds = bbox_to_bounds(bbox)
        fg1.add_child(folium.Rectangle(bounds=bounds, color=color, dash_array="5"))
        m.add_child(fg1)

    folium.GeoJson(
        data=df["geometry"],
        name="Selection",
        control=False,
        style_function=lambda x: {"fillColor": color, "color": color},
    ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    # plugins
    plugins.MiniMap(
        tile_layer="Stamen Toner",
        width=120,
        height=120,
        auto_toggle_display=True,
        zoom_level_fixed=0,
    ).add_to(m)

    plugins.Fullscreen(
        position="topright",
        title="Expand me",
        title_cancel="Exit me",
        force_separate_button=True,
    ).add_to(m)

    return m


class Page1(Page):
    def __init__(self, state, selector):
        self.state = state
        self.selector = selector

        for k, v in CONFIG_DEFAULTS.items():
            self.state[k] = v

    def write(self):

        st.title("LandscapeDNDC Preprocessing 🌎")

        # sidebar setup
        # sel_res = st.sidebar.selectbox("Select Resolution",
        #                               ['LR', 'MR', 'HR'], key=111)
        #                               value=self.state.client_config["resolution"])
        # self.state.client_config["resolution"] = sel_res

        widget_area(self)

        widget_clip(self)

        widget_main(self)
