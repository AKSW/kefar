import os
from pathlib import Path, PurePosixPath
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

import aiofiles
import jinja2
import markdown
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja_rdf import get_context, register_filters
from jinja_rdf.graph_handling import GraphToFilesystemHelper, TemplateSelectionHelper
from jinja_rdf.rdf_resource import RDFResource
from loguru import logger
from mkdocs.config.base import load_config
from mkdocs.utils import get_build_datetime, meta, normalize_url
from mkdocs.utils.templates import TemplateContext, script_tag_filter, url_filter
from rdflib import Graph, URIRef
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from rdflib.resource import Resource

import plugins.datetime_format

THEME_DIR = "templates"
DOCS_DIR = "docs"
INDEX_DOC = "index.md"
DEFAULT_TEMPLATE = "base.html"

JINJA2_AUTOESCAPE = os.environ.get("JINJA2_AUTOESCAPE", None)


class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


logger.debug(os.getcwd())

mkdocs_config = load_config()
config = mkdocs_config.plugins.get("mkrdf").config

"""The resource_to_page dict is required since there is no backward relation from resource to a page."""


def resource_iri_to_path(resource_iri: URIRef) -> str:
    gtfh = GraphToFilesystemHelper(config.base_iri)
    path, fragment = gtfh.iri_to_path(resource_iri)
    if fragment:
        return f"{path}#{fragment}"
    return path


def resolve_url(value: str | URIRef | Resource) -> str | None:
    """A Template filter to resolve an iri and return a normalized URL."""
    if isinstance(value, Resource):
        value = value.identifier
    if isinstance(value, str):
        value = URIRef(value)
    return resource_iri_to_path(value)


@jinja2.pass_context
def iri_resolver(context: TemplateContext, value: str | URIRef | Resource) -> str:
    """A Template filter to resolve an iri and return a normalized URL."""
    if url := resolve_url(value):
        pass
    else:
        if isinstance(value, Resource):
            url = value.identifier
        else:
            url = value

    # Remove the current basename from the url, to fix that the mkdocs get_relative_url() method just omits basenames with a dot.
    # Also it doesn't matter if we calculate the path relative to the current file or its directory.
    return normalize_url(
        str(url),
        page=dotdict({"url": context["page"].url.rpartition("/")[0] + "/"}),
        base=context["base_url"],
    )


def get_graph():
    if config.graph_file:
        g = Graph()
        g.parse(source=config.graph_file)
    elif config.sparql_endpoint:
        store = SPARQLStore(query_endpoint=config.sparql_endpoint)
        g = Graph(store=store)
    yield g


if not JINJA2_AUTOESCAPE:
    jinja2_autoescape = False
elif JINJA2_AUTOESCAPE == "select":
    jinja2_autoescape = jinja2.select_autoescape()
else:
    jinja2_autoescape = True


loader = jinja2.FileSystemLoader(THEME_DIR)

env = jinja2.Environment(loader=loader, autoescape=jinja2_autoescape)

register_filters(env)
env.filters["iri_resolver"] = iri_resolver
env.filters["url"] = url_filter
env.filters["script_tag"] = script_tag_filter

env.globals["config"] = mkdocs_config
env.globals["base_url"] = ""

plugins.datetime_format.on_env(env, config, [])

templates = Jinja2Templates(env=env)

GraphDep = Annotated[Graph, Depends(get_graph)]

app = FastAPI()


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def read_item(request: Request, full_path: str, graph: GraphDep):
    # First, check if a static file exists
    static_file_path = Path(THEME_DIR) / full_path
    if (
        static_file_path.exists()
        and static_file_path.is_file()
        and static_file_path.suffix != ".html"
    ):
        return FileResponse(static_file_path)

    # Second, check if we actually want to serve the resource
    # TODO implement resource selection

    # Third, build a page for the resource
    page = dotdict({"url": full_path, "meta": {}, "content": ""})

    # Check if a markdown file exists under docs at the path and read it
    doc_file_path = Path(DOCS_DIR) / full_path
    logger.debug(doc_file_path)
    if doc_file_path.exists():
        if doc_file_path.is_dir():
            doc_file_path /= INDEX_DOC
        logger.debug(doc_file_path)
        if doc_file_path.is_file() and doc_file_path.suffix == ".md":
            async with aiofiles.open(doc_file_path, "r") as doc_file:
                source = await doc_file.read()
                source_markdown, source_meta = meta.get_data(source)
                md = markdown.Markdown()
                page.content = md.convert(source_markdown)
                page.meta = source_meta

    # Define the resource IRI
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
    page.meta["resource_iri"] = resource_iri

    page.rdf_resource = RDFResource(
        graph, page.meta["resource_iri"], graph.namespace_manager
    )

    # Select template
    # NOTE: Potential extension: if multiple template candidates are available,
    # the precedence rules as in JekyllRDF should be applied,
    # but could be overwritten by setting some X-KEFAR-TEMPLATE HTTP header.
    if "template" not in page.meta:
        logger.debug("No template set, identify the template")
        template = TemplateSelectionHelper(
            graph,
            config.class_template_map,
            config.instance_template_map,
        ).get_template_for_resource(page.rdf_resource)
        if template:
            logger.debug(f"Select template: {template} for {page.rdf_resource}")
            page.meta["template"] = template
        else:
            logger.debug("No template found")
            page.meta["template"] = DEFAULT_TEMPLATE

    logger.debug(page)
    logger.debug(page.meta)

    context = {"page": page, "build_date_utc": get_build_datetime()}

    return templates.TemplateResponse(
        request=request,
        name=page.meta["template"],
        context={**get_context(graph, page.rdf_resource), **context},
    )
