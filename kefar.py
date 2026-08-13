from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from rdflib import Graph, URIRef
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from jinja_rdf.graph_handling import IRIPath, TemplateSelectionHelper
from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit
from loguru import logger

config = {}
config.graph_file = "data/websites.ttl"
config.base_iri = "https://d-nb.info/"
config.class_template_map = {
    "http://purl.org/lobid/lv#ArchivedWebPage": "archivedwebpage.html",
    "http://purl.org/ontology/bibo/Website": "website.html",
    "http://purl.org/ontology/bibo/Series": "collection.html",
    "https://github.com/DOWARC/dowarc#WARCfile": "warcfile.html",
    "https://github.com/DOWARC/dowarc#WARCrecord": "warcrecord.html",
}
config.instance_template_map = {
    "https://webarchiv.apps.dnb.de/wacalog/": "home.html"
}
config.selection = None

def get_graph():
    if config.graph_file:
        g = Graph()
        g.parse(source=config.graph_file)
    elif config.sparql_endpoint:
        store = SPARQLStore(query_endpoint=config.sparql_endpoint)
        g = Graph(store=store)
    yield g

GraphDep = Annotated[Graph, Depends(get_graph)]

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def read_item(request: Request, full_path: str, graph: GraphDep):

    page = {"url": full_path}

    base_iri = urlsplit(config.base_iri)
    logger.debug(base_iri)
    resource_iri = URIRef(
        urlunsplit(
            (
                base_iri.scheme,
                base_iri.netloc,
                str(PurePosixPath(base_iri.path) / page.url),
                "",
                "",
            )
        )
    )
    logger.info(f"Requested resource_iri: {resource_iri}")

    # --- TODO --- mkrdf.py:120

    page.rdf_resource = RDFResource(
        self.graph, page.meta["resource_iri"], self.graph.namespace_manager
    )
    self.resource_iri_to_page[page.meta["resource_iri"]] = page

    # select templates
    if "template" not in page.meta:
        template = TemplateSelectionHelper(
            self.graph,
            self.config.class_template_map,
            self.config.instance_template_map,
        ).get_template_for_resource(page.rdf_resource)
        if template:
            logger.debug(f"Select template: {template} for {page.rdf_resource}")
            page.meta["template"] = template

    return templates.TemplateResponse(
        request=request, name="item.html", context={"id": id}
    )