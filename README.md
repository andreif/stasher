# Stasher

Stash your files temporarily on a remote server.

## Install

```sh
pip install stasher
```


## Usage

```sh
export STASH_URL=https://my-secret-stash.herokuapp.com
export STASH_TOKEN=***very-secret-token***

# pushing to your stash server
stash push my-box-name myfile1.txt
stash push my-box-name myfile2.txt

# pulling from your stash server
stash pull my-box-name

# see more options
stash -h
stash push -h
stash pull -h
```

## Deploy stasher on Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/andreif/stasher)

It will generate `STASH_TOKEN` variable for you, which you can see with:

```sh
heroku config:get STASH_TOKEN
```

The token can be changed with:

```sh
heroku config:set STASH_TOKEN=***your-value***
```

### Manual deploy

Install Heroku CLI, see https://devcenter.heroku.com/articles/heroku-cli

```sh
git clone git@github.com:andreif/stasher.git
cd stasher

heroku apps:create my-secret-stash
heroku git:remote -a my-secret-stash
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set STASH_TOKEN=***very-secret-token***

git push heroku master
heroku open
```
