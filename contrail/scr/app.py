'''Creates an instance of our dash.Dash() app.

Uses an external_script NAME - allows us to ?

Sets 'app.config.suppress_callback_exceptions = True' to avoid unhelpful warnings
about callbacks that exist in accompanying python scripts.

Callbacks:

Functions:

Misc Variables:

    app
    external_scripts
    server
'''



import dash

external_scripts = ['https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML']

app = dash.Dash(__name__, external_scripts=external_scripts)

server = app.server
app.config.suppress_callback_exceptions = True