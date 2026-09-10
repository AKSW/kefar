# Kefar

> [!WARNING]
>
> ⚠️ This is proof of concept, not well tested, and might never be complete, what ever that means.

This is a dynamic site rendering system based on [Jinja RDF](https://github.com/AKSW/jinja-rdf).
It allows exploring resources from an RDF knowledge graph through webpages rendered based on Jinja templates.
In the result it is the dynamic counterpart for [MkRDF](https://github.com/aksw/mkrdf) and mocks partially the behavior of [MkDocs](https://www.mkdocs.org/) to provide an, in parts, similar environment for the templates.
💡 The idea is that pages look the same as in MkRDF, while only a subset of the MkDocs functionality is supported.

## Scalability
MkRDF is the best to shift all computing effort to the build time to serve the pages with minimum resources per request, best for many requests at a low update frequency of the graph and templates.
Kefar serves for the opposite scenario, best for a high update frequency of the graph or templates at a respectively lower request rate.

## The Name
- is an acronym of the terms, Knowledge Graph, Exploration, FastAPI, Resources;
- 🪲 sounds similar to the German word Käfer (engl. beetle);
- can be read as a transliteration of the Hebrew word כפר while k'far or kfar is more common (engl. village).
