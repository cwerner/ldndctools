import streamlit as st
import intake
import io
import sys

from ldndctools.gui.utils import provide_state
from ldndctools.gui.page1 import Page1
from ldndctools.gui.download_button import download_button

from ldndctools.io.zipwriter import ZipWriter

from ldndctools.cli.selector import Selector
from ldndctools.misc.helper import dataset_to_bytes, get_s3_link
from ldndctools.misc.types import RES

from ldndctools.misc.create_data import create_dataset

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

    file_name = st.sidebar.text_input(
        "File name", value=state.client_config["file_name"]
    )
    state.client_config["file_name"] = file_name

    b_start, b_stop, _, notify = st.sidebar.beta_columns([3, 3, 1, 6])

    with b_start:
        start = st.button("🏁 Start")

    with b_stop:
        stop = st.button("🛑 Stop")

    note = st.empty()
    return start, stop, notify, note, file_name


@provide_state()
def main(state=None):

    # def _get_cfg_item(group, item, save="na"):
    #     return cfg[group].get(item, save)
    #
    # BASEINFO = dict(
    #     AUTHOR=_get_cfg_item("info", "author"),
    #     EMAIL=_get_cfg_item("info", "email"),
    #     DATE=str(datetime.datetime.now()),
    #     DATASET=_get_cfg_item("project", "dataset"),
    #     VERSION=_get_cfg_item("project", "version", save="0.1"),
    #     SOURCE=_get_cfg_item("project", "source"),
    # )

    res = widget_resolution()

    # 110m is pretty poor - LR also gets 50m
    rmap = {RES.LR: 50, RES.MR: 50, RES.HR: 10}

    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    df = catalog.admin(res=rmap[res]).read()
    selector = Selector(df)

    # build gui
    Page1(state=state, selector=selector).write()
    start, stop, notify, note, file_name = widget_process(state)

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
            note.success(f"Processing done!")

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
