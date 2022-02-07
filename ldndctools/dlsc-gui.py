import io
import sys

import intake
import pandas as pd
import streamlit as st

from ldndctools.cli.selector import Selector
from ldndctools.gui.download_button import download_button
from ldndctools.gui.page1 import Page1
from ldndctools.io.zipwriter import ZipWriter
from ldndctools.misc.create_data import create_dataset
from ldndctools.misc.helper import dataset_to_bytes, get_s3_link
from ldndctools.misc.types import RES

if sys.version_info >= (3, 7):
    from importlib import resources


def widget_resolution():
    st.sidebar.subheader("① Choose Resolution")
    res = st.sidebar.selectbox(
        "Pick output resolution", RES.members(), format_func=lambda x: x.value
    )
    return res


def widget_process(state=None):
    st.sidebar.subheader("④ Process dataset")

    file_name = st.sidebar.text_input("File name", value=state["file_name"])
    state["file_name"] = file_name

    b_start, b_stop, _, notify = st.sidebar.columns([3, 3, 1, 6])

    with b_start:
        start = st.button("🏁 Start")

    with b_stop:
        stop = st.button("🛑 Stop")

    note = st.empty()
    return start, stop, notify, note, file_name


def load_catalog():
    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))
    return catalog


def load_admin_data(catalog, res: RES) -> pd.DataFrame:

    # 110m is pretty poor - LR also gets 50m
    res_scale_mapper = {RES.LR: 50, RES.MR: 50, RES.HR: 10}

    df = catalog.admin(scale=res_scale_mapper[res]).read()
    return df


def main():

    res = widget_resolution()

    catalog = load_catalog()

    df = load_admin_data(catalog, res)

    selector = Selector(df)

    # build gui
    Page1(state=st.session_state, selector=selector).write()
    start, stop, notify, note, file_name = widget_process(st.session_state)

    with notify:
        status_widget = st.empty()

    if stop:
        note.error("Job cancelled")
        st.stop()

    if start:
        status_widget.warning("Preparing...")

        progressbar = st.sidebar.progress(0)

        soil = catalog.soil(res=res.name).read()
        result = create_dataset(soil, selector, res, progressbar, status_widget)

        if result:
            note.success("Processing done!")

            # create byte streams for output in zip file
            xml_bytes, ds = result
            xml_buffer = io.BytesIO(xml_bytes.encode("utf-8"))
            nc_buffer = io.BytesIO(dataset_to_bytes(ds))

            if not file_name.endswith(".xml"):
                xml_name, nc_name, zip_name = [
                    f"{file_name}.{s}" for s in ["xml", "nc", "zip"]
                ]
            else:
                xml_name = file_name
                nc_name, zip_name = [
                    file_name.replace(".xml", s) for s in [".nc", ".zip"]
                ]

            zip_buffer = ZipWriter(
                [(xml_name, xml_buffer), (nc_name, nc_buffer)]
            ).write()

            uri = get_s3_link(
                buffer=zip_buffer,
                filename=f"outputs/{zip_name}",
                content_type="application/zip",
                bucket_name="ldndcdata",
            )

            note.markdown(download_button(file_name, uri), unsafe_allow_html=True)
        else:
            note.error("Something went wrong!")


if __name__ == "__main__":
    main()
