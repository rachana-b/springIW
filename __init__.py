# -*- coding: utf-8 -*-

"""
Copyright 2016 Randal S. Olson

This file is part of the Twitter Bot library.

The Twitter Bot library is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

The Twitter Bot library is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
the Twitter Bot library. If not, see http://www.gnu.org/licenses/.
"""
from __future__ import print_function
from twitter import Twitter, OAuth, TwitterHTTPError
import os
import sys
import time
import random
from datetime import datetime
import credentials

class TwitterBot:

    PASSWORD = credentials.PASSWORD
    EMAIL_PRESTRING_RB = credentials.EMAIL_PRESTRING_RB
    EMAIL_POSTSTRING = credentials.EMAIL_POSTSTRING
    
    # Format for the Twitter HANDLE
    #HANDLE_BL = "springIWbl"
    #HANDLE_THC = "springIWthc"
    HANDLE_PRESTRING = "summerRB" 

    # List of bot USERNAMES, not HANDLE
    #FULL_NAMES = ["A. A.", "A. B.", "A. C.", "A. D.", "A. E."]
    FULL_NAMES = ["summerRB00"]

    CONFIG_FOLDER = "configs"

    CONFIG_PRESTRING = "config"

    ALREADY_FOLLOWED_FILE = "already-followed"

    FOLLOWERS = "followers"

    FOLLOWS = "following"

    DOT_TXT = ".txt"

    APP_NAME_BL = "summerRB"

    APP_WEBSITE = "http://frogolandia.50megs.com/"

    PREFIX = "/vagrant/"
    LOGFILE = "log"


#remember to make cache files for all the bots. go into config and touch them 
#have them all tweet something

    """
        Bot that automates several actions on Twitter, such as following users
        and favoriting tweets.
    """

    #sets up bot 
    def __init__(self, config_file="config.txt"):
        
        # this variable contains the configuration for the bot
        self.BOT_CONFIG = {}

        # this variable contains the authorized connection to the Twitter API
        self.TWITTER_CONNECTION = None

        self.bot_setup(config_file)

        # Used for random timers
        random.seed()

    #waits between times put into config file
    def wait_on_action(self):
        min_time = 0
        max_time = 0
        if "FOLLOW_BACKOFF_MIN_SECONDS" in self.BOT_CONFIG:
            min_time = int(self.BOT_CONFIG["FOLLOW_BACKOFF_MIN_SECONDS"])

        if "FOLLOW_BACKOFF_MAX_SECONDS" in self.BOT_CONFIG:
            max_time = int(self.BOT_CONFIG["FOLLOW_BACKOFF_MAX_SECONDS"])

        if min_time > max_time:
            temp = min_time
            min_time = max_time
            max_time = temp

        wait_time = random.randint(min_time, max_time)

        if wait_time > 0:
            print("Choosing time between %d and %d - waiting %d seconds before action" % (min_time, max_time, wait_time))
            time.sleep(wait_time)

        return wait_time

    def bot_setup(self, config_file="config.txt"):
    #def bot_setup(self, config_file):
        """
            Reads in the bot configuration file and sets up the bot.

            Defaults to config.txt if no configuration file is specified.

            If you want to modify the bot configuration, edit your config.txt.
        """
        with open(config_file, "r") as in_file:
            for line in in_file:
                line = line.split(":")
                parameter = line[0].strip()
                value = line[1].strip()

                if parameter in ["USERS_KEEP_FOLLOWING", "USERS_KEEP_UNMUTED", "USERS_KEEP_MUTED"]:
                    if value != "":
                        self.BOT_CONFIG[parameter] = set([int(x) for x in value.split(",")])
                    else:
                        self.BOT_CONFIG[parameter] = set()
                elif parameter in ["FOLLOW_BACKOFF_MIN_SECONDS", "FOLLOW_BACKOFF_MAX_SECONDS"]:
                    self.BOT_CONFIG[parameter] = int(value)
                else:
                    self.BOT_CONFIG[parameter] = value

        # make sure that the config file specifies all required parameters
        required_parameters = ["OAUTH_TOKEN", "OAUTH_SECRET", "CONSUMER_KEY",
                               "CONSUMER_SECRET", "TWITTER_HANDLE",
                               "ALREADY_FOLLOWED_FILE",
                               "FOLLOWERS_FILE", "FOLLOWS_FILE"]

        missing_parameters = []

        for required_parameter in required_parameters:
            if (required_parameter not in self.BOT_CONFIG or
                    self.BOT_CONFIG[required_parameter] == ""):
                missing_parameters.append(required_parameter)

        if len(missing_parameters) > 0:
            self.BOT_CONFIG = {}
            raise Exception("Please edit %s to include the following parameters: %s.\n\n"
                            "The bot cannot run unless these parameters are specified."
                            % (config_file, ", ".join(missing_parameters)))

        # make sure all of the sync files exist locally
        for sync_file in [self.BOT_CONFIG["ALREADY_FOLLOWED_FILE"],
                          self.BOT_CONFIG["FOLLOWS_FILE"],
                          self.BOT_CONFIG["FOLLOWERS_FILE"]]:
            if not os.path.isfile(sync_file):
                with open(sync_file, "w") as out_file:
                    out_file.write("")

        # check how old the follower sync files are and recommend updating them
        # if they are old
        if (time.time() - os.path.getmtime(self.BOT_CONFIG["FOLLOWS_FILE"]) > 86400 or
                time.time() - os.path.getmtime(self.BOT_CONFIG["FOLLOWERS_FILE"]) > 86400):
            print("Warning: Your Twitter follower sync files are more than a day old. "
                  "It is highly recommended that you sync them by calling sync_follows() "
                  "before continuing.", file=sys.stderr)

        # create an authorized connection to the Twitter API
        self.TWITTER_CONNECTION = Twitter(auth=OAuth(self.BOT_CONFIG["OAUTH_TOKEN"],
                                                     self.BOT_CONFIG["OAUTH_SECRET"],
                                                     self.BOT_CONFIG["CONSUMER_KEY"],
                                                     self.BOT_CONFIG["CONSUMER_SECRET"]))

    # so you can get the timeline but its super gross...need to parse it!!
    def get_timeline(self):
        return self.TWITTER_CONNECTION.statuses.home_timeline(count=50)

    def sync_follows(self):
        """
            Syncs the user's followers and follows locally so it isn't necessary
            to repeatedly look them up via the Twitter API.

            It is important to run this method at least daily so the bot is working
            with a relatively up-to-date version of the user's follows.

            Do not run this method too often, however, or it will quickly cause your
            bot to get rate limited by the Twitter API.
        """

        # sync the user's followers (accounts following the user)
        print ("Syncing user followers")

        followers_status = self.TWITTER_CONNECTION.followers.ids(screen_name=self.BOT_CONFIG["TWITTER_HANDLE"])
        followers = set(followers_status["ids"])
        next_cursor = followers_status["next_cursor"]

        with open(self.BOT_CONFIG["FOLLOWERS_FILE"], "w") as out_file:
            for follower in followers:
                out_file.write("%s\n" % str(follower))

        while next_cursor != 0:
            followers_status = self.TWITTER_CONNECTION.followers.ids(screen_name=self.BOT_CONFIG["TWITTER_HANDLE"],
                                                                     cursor=next_cursor)
            followers = set(followers_status["ids"])
            next_cursor = followers_status["next_cursor"]

            with open(self.BOT_CONFIG["FOLLOWERS_FILE"], "a") as out_file:
                for follower in followers:
                    out_file.write("%s\n" % str(follower))


        # sync the user's follows (accounts the user is following)
        print ("Syncing user followees")

        following_status = self.TWITTER_CONNECTION.friends.ids(screen_name=self.BOT_CONFIG["TWITTER_HANDLE"])
        #print (following_status)
        following = set(following_status["ids"])
        #print(following)
        next_cursor = following_status["next_cursor"]

        with open(self.BOT_CONFIG["FOLLOWS_FILE"], "w") as out_file:
            for follow in following:
                out_file.write("%s\n" % str(follow))

        while (next_cursor != 0):
            following_status = self.TWITTER_CONNECTION.friends.ids(screen_name=self.BOT_CONFIG["TWITTER_HANDLE"],
                                                                   cursor=next_cursor)
            following = set(following_status["ids"])
            next_cursor = following_status["next_cursor"]

            with open(self.BOT_CONFIG["FOLLOWS_FILE"], "a") as out_file:
                for follow in following:
                    out_file.write("%s\n" % str(follow))

    def get_do_not_follow_list(self):
        """
            Returns the set of users the bot has already followed in the past.
        """

        dnf_list = []
        with open(self.BOT_CONFIG["ALREADY_FOLLOWED_FILE"], "r") as in_file:
            for line in in_file:
                dnf_list.append(int(line))

        return set(dnf_list)

    def get_followers_list(self):
        """
            Returns the set of users that are currently following the user.
        """

        followers_list = []
        with open(self.BOT_CONFIG["FOLLOWERS_FILE"], "r") as in_file:
            for line in in_file:
                followers_list.append(int(line))

        return set(followers_list)

    def get_follows_list(self):
        """
            Returns the set of users that the user is currently following.
        """
        follows_list = []
        with open(self.BOT_CONFIG["FOLLOWS_FILE"], "r") as in_file:
            for line in in_file:
                follows_list.append(int(line))

        return set(follows_list)

    def search_tweets(self, phrase, count=100, result_type="recent"):
        """
            Returns a list of tweets matching a phrase (hashtag, word, etc.).
        """

        return self.TWITTER_CONNECTION.search.tweets(q=phrase, result_type=result_type, count=count)

    def get_recent(self):
        """
            Returns a list of 100 most recent tweets
        """
        return self.TWITTER_CONNECTION.search.tweets(q=" ", result_type="recent", count=20)

    def auto_fav(self, phrase, count=100, result_type="recent"):
        """
            Favorites tweets that match a phrase (hashtag, word, etc.).
        """

        result = self.search_tweets(phrase, count, result_type)

        for tweet in result["statuses"]:
            try:
                # don't favorite your own tweets
                if tweet["user"]["screen_name"] == self.BOT_CONFIG["TWITTER_HANDLE"]:
                    continue
                
                self.wait_on_action()
                
                result = self.TWITTER_CONNECTION.favorites.create(_id=tweet["id"])
                print("Favorited: %s" % (result["text"].encode("utf-8")), file=sys.stdout)

            # when you have already favorited a tweet, this error is thrown
            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "rate limit" in str(api_error).lower():
                    print("You have been rate limited. "
                          "Wait a while before running the bot again.", file=sys.stderr)
                    return

                if "you have already favorited this status" not in str(api_error).lower():
                    print("Error: %s" % (str(api_error)), file=sys.stderr)

    def auto_rt(self, phrase, count=100, result_type="recent"):
        """
            Retweets tweets that match a phrase (hashtag, word, etc.).
        """

        result = self.search_tweets(phrase, count, result_type)

        for tweet in result["statuses"]:
            try:
                # don't retweet your own tweets
                if tweet["user"]["screen_name"] == self.BOT_CONFIG["TWITTER_HANDLE"]:
                    continue
                
                self.wait_on_action()
                
                result = self.TWITTER_CONNECTION.statuses.retweet(id=tweet["id"])
                print("Retweeted: %s" % (result["text"].encode("utf-8")), file=sys.stdout)

            # when you have already retweeted a tweet, this error is thrown
            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "rate limit" in str(api_error).lower():
                    print("You have been rate limited. "
                          "Wait a while before running the bot again.", file=sys.stderr)
                    return

                print("Error: %s" % (str(api_error)), file=sys.stderr)

    def auto_follow(self, phrase, count=100, result_type="recent"):
        """
            Follows anyone who tweets about a phrase (hashtag, word, etc.).
        """

        result = self.search_tweets(phrase, count, result_type)
        following = self.get_follows_list()
        do_not_follow = self.get_do_not_follow_list()

        for tweet in result["statuses"]:
            try:
                if (tweet["user"]["screen_name"] != self.BOT_CONFIG["TWITTER_HANDLE"] and
                        tweet["user"]["id"] not in following and
                        tweet["user"]["id"] not in do_not_follow):

                    self.wait_on_action()

                    self.TWITTER_CONNECTION.friendships.create(user_id=tweet["user"]["id"], follow=False)
                    following.update(set([tweet["user"]["id"]]))

                    print("Followed %s" %
                          (tweet["user"]["screen_name"]), file=sys.stdout)

            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "unable to follow more people at this time" in str(api_error).lower():
                    print("You are unable to follow more people at this time. "
                          "Wait a while before running the bot again or gain "
                          "more followers.", file=sys.stderr)
                    return

                # don't print "already requested to follow" errors - they're
                # frequent
                if "already requested to follow" not in str(api_error).lower():
                    print("Error: %s" % (str(api_error)), file=sys.stderr)

    def auto_follow_followers(self,count=None):
        """
            Follows back everyone who's followed you.
        """

        following = self.get_follows_list()
        followers = self.get_followers_list()

        not_following_back = followers - following
        not_following_back = list(not_following_back)[:count]
        for user_id in not_following_back:
            try:
                self.wait_on_action()

                self.TWITTER_CONNECTION.friendships.create(user_id=user_id, follow=False)
            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "unable to follow more people at this time" in str(api_error).lower():
                    print("You are unable to follow more people at this time. "
                          "Wait a while before running the bot again or gain "
                          "more followers.", file=sys.stderr)
                    return

                # don't print "already requested to follow" errors - they're frequent
                if "already requested to follow" not in str(api_error).lower():
                    print("Error: %s" % (str(api_error)), file=sys.stderr)

    def auto_follow_followers_of_user(self, user_twitter_handle, count=100):
        """
            Follows the followers of a specified user.
        """

        following = self.get_follows_list()
        followers_of_user = set(self.TWITTER_CONNECTION.followers.ids(screen_name=user_twitter_handle)["ids"][:count])
        do_not_follow = self.get_do_not_follow_list()

        for user_id in followers_of_user:
            try:
                if (user_id not in following and
                        user_id not in do_not_follow):

                    self.wait_on_action()

                    self.TWITTER_CONNECTION.friendships.create(user_id=user_id, follow=False)
                    print("Followed %s" % user_id, file=sys.stdout)

            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "unable to follow more people at this time" in str(api_error).lower():
                    print("You are unable to follow more people at this time. "
                          "Wait a while before running the bot again or gain "
                          "more followers.", file=sys.stderr)
                    return

                # don't print "already requested to follow" errors - they're
                # frequent
                if "already requested to follow" not in str(api_error).lower():
                    print("Error: %s" % (str(api_error)), file=sys.stderr)

    def auto_unfollow_nonfollowers(self,count=None):
        """
            Unfollows everyone who hasn't followed you back.
        """

        following = self.get_follows_list()
        followers = self.get_followers_list()

        not_following_back = following - followers
        not_following_back = list(not_following_back)[:count]
        # update the "already followed" file with users who didn't follow back
        already_followed = set(not_following_back)
        already_followed_list = []
        with open(self.BOT_CONFIG["ALREADY_FOLLOWED_FILE"], "r") as in_file:
            for line in in_file:
                already_followed_list.append(int(line))

        already_followed.update(set(already_followed_list))

        with open(self.BOT_CONFIG["ALREADY_FOLLOWED_FILE"], "w") as out_file:
            for val in already_followed:
                out_file.write(str(val) + "\n")

        for user_id in not_following_back:
            if user_id not in self.BOT_CONFIG["USERS_KEEP_FOLLOWING"]:

                self.wait_on_action()

                self.TWITTER_CONNECTION.friendships.destroy(user_id=user_id)
                print("Unfollowed %d" % (user_id), file=sys.stdout)

    def auto_unfollow_all_followers(self,count=None):
        """
            Unfollows everyone that you are following(except those who you have specified not to)
        """
        following = self.get_follows_list()

        for user_id in following:
            if user_id not in self.BOT_CONFIG["USERS_KEEP_FOLLOWING"]:

                self.wait_on_action()

                self.TWITTER_CONNECTION.friendships.destroy(user_id=user_id)
                print("Unfollowed %d" % (user_id), file=sys.stdout)

    def auto_unfollow_converagance(self, count, num):
        """
        Unfollows a specified number of users to stay at converance limit
        """
        following = self.get_follows_list()

        logpath = TwitterBot.PREFIX + TwitterBot.LOGFILE + str(num) + TwitterBot.DOT_TXT
        f = open(logpath, "a")
        cnt = 0
        i = 0
        while cnt < count:
            r = random.random()
            if r <0.5:
                self.wait_on_action()
                self.TWITTER_CONNECTION.friendships.destroy(user_id=following[i])
                rec = (self.BOT_CONFIG["TWITTER_HANDLE"] + " unfollowed " + following[i] + " at " + 
                        str(datetime.now()) + "\n")
                f.write(rec)
                cnt += 1
            i += 1

    def auto_mute_following(self):
        """
            Mutes everyone that you are following.
        """

        following = self.get_follows_list()
        muted = set(self.TWITTER_CONNECTION.mutes.users.ids(screen_name=self.BOT_CONFIG["TWITTER_HANDLE"])["ids"])

        not_muted = following - muted

        for user_id in not_muted:
            if user_id not in self.BOT_CONFIG["USERS_KEEP_UNMUTED"]:
                self.TWITTER_CONNECTION.mutes.users.create(user_id=user_id)
                print("Muted %d" % (user_id), file=sys.stdout)

    def auto_unmute(self):
        """
            Unmutes everyone that you have muted.
        """

        muted = set(self.TWITTER_CONNECTION.mutes.users.ids(screen_name=self.BOT_CONFIG["TWITTER_HANDLE"])["ids"])

        for user_id in muted:
            if user_id not in self.BOT_CONFIG["USERS_KEEP_MUTED"]:
                self.TWITTER_CONNECTION.mutes.users.destroy(user_id=user_id)
                print("Unmuted %d" % (user_id), file=sys.stdout)

    def send_tweet(self, message):
        """
            Posts a tweet.
        """

        return self.TWITTER_CONNECTION.statuses.update(status=message)
    
    def auto_add_to_list(self, phrase, list_slug, count=100, result_type="recent"):
        """
            Add users to list slug that are tweeting phrase.
        """
        
        result = self.search_tweets(phrase, count, result_type)
        
        for tweet in result["statuses"]:
            try:
                if tweet["user"]["screen_name"] == self.BOT_CONFIG["TWITTER_HANDLE"]:
                    continue
                
                result = self.TWITTER_CONNECTION.lists.members.create(owner_screen_name=self.BOT_CONFIG["TWITTER_HANDLE"],
                                                                      slug=list_slug,
                                                                      screen_name=tweet["user"]["screen_name"])
                print("User %s added to the list %s" % (tweet["user"]["screen_name"], list_slug), file=sys.stdout)
            except TwitterHTTPError as api_error:
                print(api_error)

    def follow_retweeted_users(self, num, numTweets):
        """
            Find users who have been retweeted and follow them
        """
        result = self.get_timeline()
        print(len(result))
        
        following = self.get_follows_list()
        #print(following)

        logpath = TwitterBot.PREFIX + TwitterBot.LOGFILE + str(num) + TwitterBot.DOT_TXT
        # print(logpath)
        f = open(logpath, "a")

        for x in xrange(numTweets)
        # for tweet in result:
            tweet = result[x]
            try:
                print(tweet["user"]["screen_name"])
                if (tweet["user"]["screen_name"] != self.BOT_CONFIG["TWITTER_HANDLE"] and
                        tweet["user"]["id"] not in following and tweet["user"]["id"] != prev):
                    # prevents prolific retweeters
                    self.wait_on_action()
                    self.TWITTER_CONNECTION.friendships.create(user_id=tweet["user"]["id_str"], follow=False)
                    following.update(set([tweet["user"]["id_str"]]))

                    print("Followed %s" %
                          (tweet["user"]["name"]), file=sys.stdout)
                    rec = (self.BOT_CONFIG["TWITTER_HANDLE"] + " followed " + tweet["user"]["screen_name"] 
                        + " at " + str(datetime.now()) + "\n")
                    f.write(rec)

                if ("RT @" in tweet["text"]):
                    handle = tweet["text"].split("RT @")[1].split()[0][:-1]
                    self.wait_on_action()
                    self.TWITTER_CONNECTION.friendships.create(screen_name=handle, follow=False)
                    
                    print("Followed %s" % handle, file=sys.stdout)
                    rec = (self.BOT_CONFIG["TWITTER_HANDLE"] + " followed " + handle + " at " + 
                        str(datetime.now()) + " retweeted by " + tweet["user"]["screen_name"] + "\n")
                    f.write(rec)

            except TwitterHTTPError as api_error:
                # quit on rate limit errors
                if "unable to follow more people at this time" in str(api_error).lower():
                    print("You are unable to follow more people at this time. "
                          "Wait a while before running the bot again or gain "
                          "more followers.", file=sys.stderr)
                    return

                # don't print "already requested to follow" errors - they're
                # frequent
                #if "already requested to follow" not in str(api_error).lower():
                print("Error: %s" % (str(api_error)), file=sys.stderr)

        return following







