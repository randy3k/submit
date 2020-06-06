from flask import Flask, render_template, redirect, url_for, session, request
from flask import flash
from flask_dance.contrib.github import make_github_blueprint, github
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from collections import namedtuple
import functools
import gspread
import os
from datetime import datetime
import pytz
import requests


load_dotenv()
gc = gspread.service_account("service_account.json")
worksheet141b = gc.open_by_key(os.environ["STA141B_SHEET_ID"]).get_worksheet(0)
worksheet141c = gc.open_by_key(os.environ["STA141C_SHEET_ID"]).get_worksheet(0)


app = Flask(__name__)
# otherwise flask dance thinks it is http
app.wsgi_app = ProxyFix(app.wsgi_app)

if os.environ.get("FLASK_ENV", "development") == "development":
    app.secret_key = "local testing"
    os.environ['FLASK_ENV'] = "development"
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    host = "localhost"
    github_blueprint = make_github_blueprint(
        client_id=os.environ.get("GITHUB_CLIENT_ID_DEVELOP"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET_DEVELOP"),
        redirect_to="getlogin",
        scope="")
else:
    app.secret_key = os.urandom(20).hex()
    host = "0.0.0.0"
    github_blueprint = make_github_blueprint(
        client_id=os.environ.get("GITHUB_CLIENT_ID"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
        redirect_to="getlogin",
        scope="")

app.register_blueprint(github_blueprint, url_prefix='/login')


def login_required(func):
    @functools.wraps(func)
    def _(*args, **kwargs):
        if not github.authorized:
            session["previous_url"] = request.path
            return(redirect(url_for("github.login")))

        return func(*args, **kwargs)

    return _


Parameters = namedtuple("Parameters", ["repo", "shiny", "remark"])


def get_params():
    repo = request.args.get("repo", "").strip()
    shiny = request.args.get("shiny", "").strip()
    remark = request.args.get("remark", "").strip()
    return Parameters(repo=repo, shiny=shiny, remark=remark)


@app.route("/login")
def login():
    return(redirect(url_for("github.login")))


@app.route("/logout")
def logout():
    if github.authorized:
        session.clear()
    return redirect(url_for("home"))


@app.route("/getlogin")
def getlogin():
    if github.authorized:
        if "login" not in session:
            # try three times before we gave up
            for i in range(3):
                resp = github.get("/user")
                if resp.ok:
                    break
            if not resp.ok:
                session.clear()
                return redirect(url_for("home"))

            session["login"] = resp.json()["login"]

    if "previous_url" in session:
        previous_url = session["previous_url"]
        session.pop("previous_url", None)
        if github.authorized:
            return redirect(previous_url)

    return redirect(url_for("home"))


@app.route("/141b/submit")
@login_required
def sta141b_submit():
    course_home = redirect(url_for("sta141b"))
    params = get_params()
    session["repo141b"] = params.repo
    session["shiny141b"] = params.shiny
    session["remark141b"] = params.remark

    if not params.repo.startswith("https://www.github.com/") and \
            not params.repo.startswith("https://github.com/") and \
            not params.repo.startswith("www.github.com/") and \
            not params.repo.startswith("github.com/"):

        flash("ERROR: invalid repo", "danger")
        return course_home
    if "shinyapps.io" not in params.shiny and "run.app" not in params.shiny:
        flash("ERROR: invalid shiny app url", "danger")
        return course_home

    if not requests.get(params.repo).ok:
        flash("WARNING: it seems that the repo is not approachable (maybe it is private!?)", "warning")

    if not requests.get(params.shiny).ok:
        flash("WARNING: it seems that the shiny app url is not approachable", "warning")

    alllogins = worksheet141b.col_values(1)[1:]
    login = session["login"]
    timestamp = datetime.now(pytz.timezone('America/Los_Angeles')).strftime("%Y/%m/%d %H:%M:%S")
    data = [login, params.repo, params.shiny, params.remark, timestamp]

    if login in alllogins:
        rownum = alllogins.index(login) + 2
        worksheet141b.update(f"A{rownum}:E{rownum}", [data])
        flash("Old submission is found, the new submission will overwrite the old one.", "warning")
        return course_home

    worksheet141b.append_row(data)

    flash("Submission successful.")

    return course_home


@app.route("/141c/submit")
@login_required
def sta141c_submit():
    course_home = redirect(url_for("sta141c"))
    params = get_params()
    session["repo141c"] = params.repo
    session["remark141c"] = params.remark

    if not params.repo.startswith("https://www.github.com/") and \
            not params.repo.startswith("https://github.com/") and \
            not params.repo.startswith("www.github.com/") and \
            not params.repo.startswith("github.com/"):

        flash("ERROR: invalid repo", "danger")
        return course_home

    if not requests.get(params.repo).ok:
        flash("WARNING: it seems that the repo is not approachable (maybe it is private!?)", "warning")

    alllogins = worksheet141c.col_values(1)[1:]
    login = session["login"]
    timestamp = datetime.now(pytz.timezone('America/Los_Angeles')).strftime("%Y/%m/%d %H:%M:%S")
    data = [login, params.repo, params.remark, timestamp]

    if login in alllogins:
        rownum = alllogins.index(login) + 2
        worksheet141c.update(f"A{rownum}:D{rownum}", [data])
        flash("Old submission is found, the new submission will overwrite the old one.", "warning")
        return course_home

    worksheet141c.append_row(data)

    flash("Submission successful.")

    return course_home


@app.route("/141b/")
@login_required
def sta141b():
    return render_template(
        "141b.html",
        authorized=github.authorized,
        login=session.get("login", None),
        client_id=github_blueprint.client_id,
        repo=session.get("repo141b", ""),
        shiny=session.get("shiny141b", ""),
        remark=session.get("remark141b", "")
        )


@app.route("/141c/")
@login_required
def sta141c():
    return render_template(
        "141c.html",
        authorized=github.authorized,
        login=session.get("login", None),
        client_id=github_blueprint.client_id,
        repo=session.get("repo141c", ""),
        remark=session.get("remark141c", "")
        )


@app.route("/")
def home():
    return render_template(
        "index.html",
        authorized=github.authorized,
        login=session.get("login", None),
        client_id=github_blueprint.client_id
        )


if __name__ == "__main__":

    app.run(host=host, port=8080)
