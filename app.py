# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy import ARRAY
from forms import *
from flask_migrate import Migrate


# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = "Venue"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(ARRAY(db.String))
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website_link = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship("Show", backref="Venue", lazy=True)

    def __repr__(self):
        return f"<Venue {self.id}: {self.name}>"


class Artist(db.Model):
    __tablename__ = "Artist"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(ARRAY(db.String))
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website_link = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship("Show", backref="Artist", lazy=True)

    def __repr__(self):
        return f"<Artist {self.id}: {self.name}>"


class Show(db.Model):
    __tablename__ = "Show"
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    venue_id = db.Column(db.Integer, db.ForeignKey("Venue.id"), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey("Artist.id"), nullable=False)

    def __repr__(self):
        return f"<Show {self.id}: {self.start_time}>"


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale="en")


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    city_states = db.session.query(Venue.city, Venue.state).distinct().all()
    data = []

    for city, state in city_states:
        venues = Venue.query.filter_by(city=city, state=state).all()
        venues_data = [
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(
                    [show for show in venue.shows if show.start_time > datetime.now()]
                ),
            }
            for venue in venues
        ]

        data.append({"city": city, "state": state, "venues": venues_data})

    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    search_term = request.form.get("search_term", "")
    venues = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()

    response = {
        "count": len(venues),
        "data": [{"id": venue.id, "name": venue.name} for venue in venues],
    }
    return render_template(
        "pages/search_venues.html", results=response, search_term=search_term
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first()
    upcoming_shows_count = len(
        [show for show in venue.shows if show.start_time > datetime.now()]
    )
    past_shows_count = len(
        [show for show in venue.shows if show.start_time < datetime.now()]
    )
    upcoming_shows = []
    past_shows = []

    for show in venue.shows:
        db_data = (
            db.session.query(Artist.id, Artist.name, Artist.image_link)
            .filter_by(id=show.artist_id)
            .first()
        )
        artist = {
            "artist_id": db_data.id,
            "artist_name": db_data.name,
            "artist_image_link": db_data.image_link,
            "start_time": str(show.start_time),
        }
        if show.start_time > datetime.now():
            upcoming_shows.append(artist)
        else:
            past_shows.append(artist)

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website_link": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "image_link": venue.image_link,
        "upcoming_shows": upcoming_shows,
        "past_shows": past_shows,
        "upcoming_shows_count": upcoming_shows_count,
        "past_shows_count": past_shows_count,
    }
    return render_template("pages/show_venue.html", venue=data)


#  Create Venue
#  ----------------------------------------------------------------


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    error = False

    try:
        name = request.form.get("name")
        city = request.form.get("city")
        state = request.form.get("state")
        address = request.form.get("address")
        phone = request.form.get("phone")
        genres = request.form.getlist("genres")
        facebook_link = request.form.get("facebook_link")
        image_link = request.form.get("image_link")
        website_link = request.form.get("website_link")
        seeking_talent = request.form.get("seeking_talent") == "y"
        seeking_description = request.form.get("seeking_description")

        new_venue = Venue(
            name=name,
            city=city,
            state=state,
            address=address,
            phone=phone,
            genres=genres,
            facebook_link=facebook_link,
            image_link=image_link,
            website_link=website_link,
            seeking_talent=seeking_talent,
            seeking_description=seeking_description,
        )

        db.session.add(new_venue)
        db.session.commit()

        flash("Venue " + request.form["name"] + " was successfully listed!")

    except Exception as e:
        print(e)
        error = True

        flash(
            "An error occurred. Venue " + request.form["name"] + " could not be listed."
        )

    finally:
        db.session.close()

    if error:
        return redirect(url_for("create_venue_form"))
    else:
        return redirect(url_for("index"))


#  Artists
#  ----------------------------------------------------------------
@app.route("/artists")
def artists():
    data = []
    for artist in Artist.query.all():
        artist_name = {"id": artist.id, "name": artist.name}
        data.append(artist_name)
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    search_term = request.form.get("search_term", "")
    artists = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()

    response = {
        "count": len(artists),
        "data": [{"id": artist.id, "name": artist.name} for artist in artists],
    }
    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first()
    upcoming_shows_count = len(
        [show for show in artist.shows if show.start_time > datetime.now()]
    )
    past_shows_count = len(
        [show for show in artist.shows if show.start_time < datetime.now()]
    )
    upcoming_shows = []
    past_shows = []

    for show in artist.shows:
        db_data = (
            db.session.query(Venue.id, Venue.name, Venue.image_link)
            .filter_by(id=show.artist_id)
            .first()
        )
        venue = {
            "venue_id": db_data.id,
            "venue_name": db_data.name,
            "venue_image_link": db_data.image_link,
            "start_time": str(show.start_time),
        }
        if show.start_time > datetime.now():
            upcoming_shows.append(venue)
        else:
            past_shows.append(venue)

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website_link": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "image_link": artist.image_link,
        "upcoming_shows": upcoming_shows,
        "past_shows": past_shows,
        "upcoming_shows_count": upcoming_shows_count,
        "past_shows_count": past_shows_count,
    }
    return render_template("pages/show_artist.html", artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.filter_by(id=artist_id).first()

    form = ArtistForm(obj=artist)
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first()
    artist.name = request.form.get("name")
    artist.city = request.form.get("city")
    artist.state = request.form.get("state")
    artist.phone = request.form.get("phone")
    artist.genres = request.form.getlist("genres")
    artist.facebook_link = request.form.get("facebook_link")
    artist.image_link = request.form.get("image_link")
    artist.website_link = request.form.get("website_link")
    artist.seeking_venue = request.form.get("seeking_venue") == "y"
    artist.seeking_description = request.form.get("seeking_description")

    db.session.commit()

    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.filter_by(id=venue_id).first()
    form = VenueForm(obj=venue)
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first()
    venue.name = request.form.get("name")
    venue.city = request.form.get("city")
    venue.state = request.form.get("state")
    venue.phone = request.form.get("phone")
    venue.address = request.form.get("address")
    venue.genres = request.form.getlist("genres")
    venue.facebook_link = request.form.get("facebook_link")
    venue.image_link = request.form.get("image_link")
    venue.website_link = request.form.get("website_link")
    venue.seeking_talent = request.form.get("seeking_talent") == "y"
    venue.seeking_description = request.form.get("seeking_description")
    try:
        db.session.commit()
        flash("Venue " + request.form["name"] + " was successfully updated!")
    except:
        db.session.rollback()
        flash(
            "An error occurred. Venue "
            + request.form["name"]
            + " could not be updated."
        )
    finally:
        db.session.close()
    return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    error = False

    try:
        name = request.form.get("name")
        city = request.form.get("city")
        state = request.form.get("state")
        phone = request.form.get("phone")
        genres = request.form.getlist("genres")
        facebook_link = request.form.get("facebook_link")
        image_link = request.form.get("image_link")
        website_link = request.form.get("website_link")
        seeking_venue = request.form.get("seeking_venue") == "y"
        seeking_description = request.form.get("seeking_description")

        new_artist = Artist(
            name=name,
            city=city,
            state=state,
            phone=phone,
            genres=genres,
            facebook_link=facebook_link,
            image_link=image_link,
            website_link=website_link,
            seeking_venue=seeking_venue,
            seeking_description=seeking_description,
        )

        db.session.add(new_artist)
        db.session.commit()

        flash("Artist " + name + " was successfully listed!")

    except Exception as e:
        print(e)
        error = True

        flash("An error occurred. Artist " + name + " could not be listed.")

    finally:
        db.session.close()

    if error:
        return redirect(url_for("create_artist_form"))
    else:
        return redirect(url_for("index"))


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    data = []
    all_shows = Show.query.all()

    for show in all_shows:
        artist = (
            db.session.query(Artist.id, Artist.name, Artist.image_link)
            .filter_by(id=show.artist_id)
            .first()
        )
        venue = (
            db.session.query(Venue.id, Venue.name, Venue.image_link)
            .filter_by(id=show.venue_id)
            .first()
        )
        show = {
            "venue_id": venue.id,
            "venue_name": venue.name,
            "artist_id": artist.id,
            "artist_name": artist.name,
            "artist_image_link": artist.image_link,
            "start_time": str(show.start_time),
        }
        data.append(show)

    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    error = False

    try:
        venue_id = request.form.get("venue_id")
        artist_id = request.form.get("artist_id")
        start_time = request.form.get("start_time")

        new_show = Show(venue_id=venue_id, artist_id=artist_id, start_time=start_time)

        db.session.add(new_show)
        db.session.commit()
        flash(
            "Show at start time "
            + request.form["start_time"]
            + " was successfully listed!"
        )

    except Exception as e:
        print(e)
        error = True

        flash(
            "An error occurred. Show at start time "
            + request.form["start_time"]
            + " could not be listed."
        )

    finally:
        db.session.close()

    if error:
        return redirect(url_for("create_shows"))
    else:
        return redirect(url_for("index"))


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    app.run()
