"""
Running Instructions for the Twitter Clone Program:
1. Connect to the database and run main()
2. At the prompt, choose one of the following options:
   - Enter '1' to log in with an existing user account.
   - Enter '2' to register a new user account.
   - Enter '3' to exit the program.
3. Once logged in, you will be presented with the user interface. Choose an option by entering the corresponding letter:
   - 'd' to display tweets.
   - 's' to search for tweets.
   - 'u' to search for users.
   - 'c' to compose a tweet.
   - 'l' to list followers.
   - 'q' to log out and return to the main menu.
4. To exit the program from the main menu, enter '3' again.

We assume that there are no private accounts. All accounts are public.
However, tweet feed would only show followings tweets.
Other public tweets can be accessed through search
"""

import sqlite3
import sys
import datetime
import maskpass

current_user_id = None

# Connect to the SQLite database
database = None
conn = sqlite3.connect(database)
cursor = conn.cursor()

def login():
    usr = input("Enter user id: ")
    pwd = maskpass.askpass("Enter password: ")
    
    # Check if the email and pwd match an entry in the users table
    cursor.execute('SELECT usr FROM users WHERE usr = ? AND pwd = ?', (usr, pwd))
    account = cursor.fetchone()
    
    if account:
        # User is logged in, display tweets
        print("\nLogin successful!\n")
        global current_user_id
        current_user_id = account[0] 
        user_interface(current_user_id)
    else:
        print("Invalid login credentials. Please try again or register if you are a new user.")
    return

def register():
    try:
        print("\nRegistration")
        name = input("Enter your name: ")
        email = input("Enter your email: ")
        city = input("Enter your city: ")
        timezone = input("Enter your timezone: ")
        pwd = input("Create a password: ")
        
        # Generate a unique user ID
        cursor.execute('SELECT MAX(usr) FROM users')
        max_usr = cursor.fetchone()[0]
        usr = max_usr + 1 if max_usr is not None else 1
        
        # Insert the new user into the users table
        cursor.execute('INSERT INTO users (usr, pwd, name, email, city, timezone) VALUES (?, ?, ?, ?, ?, ?)',
                       (usr, pwd, name, email, city, timezone))
        conn.commit()
        
        print(f"Registration successful. Your user ID is: {usr}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return

def search_tweets(usr):
    try:
        keywords = input("Enter keyword(s) separated by space: ").split()
        keyword_conditions = " OR ".join([
            f"t.text LIKE '%{keyword}%'" for keyword in keywords
        ])

        offset = 0
        while True:
            query = f'''
            SELECT DISTINCT t.tid, t.writer, t.tdate, t.text
            FROM tweets t
            LEFT JOIN mentions m ON t.tid = m.tid
            WHERE {keyword_conditions}
            ORDER BY t.tdate DESC
            LIMIT 5 OFFSET {offset}
            '''
            
            cursor.execute(query)
            tweets = cursor.fetchall()

            if not tweets:
                print("No more tweets found.")
                return

            # Display tweets
            for idx, tweet in enumerate(tweets, start=1):
                print(f"{idx}. {tweet[3]} (Date: {tweet[2]})")
            
            # Handle tweet selection
            tweet_selection = input("Select a tweet number for more options, 'n' for next page, or 'b' to go back: ")
            if tweet_selection.lower() == 'n':
                offset += 5
                continue
            elif tweet_selection.lower() == 'b' and offset >= 5:
                offset -= 5
                continue
            elif tweet_selection.lower() == "b" and offset < 5:
                return
            elif tweet_selection.isdigit() and 1 <= int(tweet_selection) <= len(tweets):
                selected_tweet = tweets[int(tweet_selection) - 1]
                tweet_id = selected_tweet[0]
                print(f"Selected tweet: {selected_tweet[3]}")
                # Show tweet statistics, reply, or retweet options
                action = input("Choose 'stats' for statistics, 'reply' to reply, or 'retweet' to retweet: ")
                if action.lower() == 'stats':
                    display_tweet_statistics(tweet_id)
                elif action.lower() == 'reply':
                    compose_reply(tweet_id, usr)
                elif action.lower() == 'retweet':
                    retweet(tweet_id, usr)
            else:
                print("Invalid selection. Please try again.")
                
    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return

def search_users(user_id=None):
    keyword = input("Enter a keyword to search for users: ").strip()
    sanitized_keyword = f"%{keyword}%".lower()  # Sanitize the keyword

    try:
        base_query = '''
            SELECT usr, name, city FROM users
            WHERE LOWER(name) LIKE ?
        '''
        
        cursor.execute(base_query, (sanitized_keyword,))
        name_matches = cursor.fetchall()

        base_query = '''
            SELECT usr, name, city FROM users
            WHERE LOWER(name) NOT LIKE ?
            AND LOWER(city) LIKE ?
        '''
        cursor.execute(base_query, (sanitized_keyword, sanitized_keyword))
        city_matches = cursor.fetchall()

        # sort results matched by name and city seperately and combine them
        name_matches.sort(key=lambda x: len(x[1]))
        city_matches.sort(key=lambda x: len(x[2]))
        users = name_matches + city_matches

        if not users:
            print("No users found.")
            return
        
        # Pagination and display logic
        page = 0
        while True:
            start_index = page * 5
            end_index = start_index + 5
            current_page_users = users[start_index:end_index]
            
            if not current_page_users:
                print("No more users to display.")
                return

            for user in current_page_users:
                print(f"UserID: {user[0]}, Name: {user[1]}, City: {user[2]}")

            selected_user = input("Enter a UserID to see more information, 'next' for more users, or 'back' to return: ").strip()
            if selected_user.isdigit():
                display_user_details(int(selected_user))
            elif selected_user == 'next':
                page += 1
            elif selected_user == 'back':
                return
            else:
                print("Invalid input, please try again.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    return

def display_user_details(user_id):
    try:
        # Fetch user details
        cursor.execute('''
            SELECT name, email, city, timezone FROM users WHERE usr = ?
        ''', (user_id,))
        user_details = cursor.fetchone()

        # Fetch user's tweet count, followers, and following counts
        cursor.execute('''
            SELECT
            (SELECT COUNT(*) FROM tweets WHERE writer = ?) as tweet_count,
            (SELECT COUNT(*) FROM follows WHERE flwee = ?) as following_count,
            (SELECT COUNT(*) FROM follows WHERE flwer = ?) as follower_count
        ''', (user_id, user_id, user_id))
        counts = cursor.fetchone()

        # Fetch up to 3 most recent tweets
        cursor.execute('''
            SELECT tid, text FROM tweets WHERE writer = ? ORDER BY tdate DESC LIMIT 3
        ''', (user_id,))
        recent_tweets = cursor.fetchall()

        # Displaying the details
        print(f"User ID: {user_id} Details:")
        print(f"Name: {user_details[0]}")
        print(f"Email: {user_details[1]}")
        print(f"City: {user_details[2]}")
        print(f"Timezone: {user_details[3]}")
        print(f"Number of Tweets: {counts[0]}")
        print(f"Number of Following: {counts[1]}")
        print(f"Number of Followers: {counts[2]}")
        print("Most Recent Tweets:")
        for tweet in recent_tweets:
            print(f"Tweet ID: {tweet[0]}, Tweet: {tweet[1]}")

        # Actions
        while True:  # Loop to allow user to go back
            action = input("Choose 'follow' to follow this user, 'reply' to reply to a tweet, 'retweet' to retweet, 'tweets' to see more tweets, or 'back' to go back: ").strip().lower()
            if action == 'follow':
                follow_user(user_id)
            elif action == 'reply':
                tweet_id = input("Enter the Tweet ID you want to reply to: ").strip()
                if tweet_id.isdigit():
                    compose_reply(int(tweet_id), current_user_id)
            elif action == 'retweet':
                tweet_id = input("Enter the Tweet ID you want to retweet: ").strip()
                if tweet_id.isdigit():
                    retweet(int(tweet_id), current_user_id)
            elif action == 'tweets':
                display_more_tweets(user_id)
            elif action == 'back':
                user_interface(current_user_id)  # Call the user interface function to go back
                return  # Exit the loop to prevent further input after going back
            else:
                print("Invalid option.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    return

def follow_user(target_user_id):
    try:
        cursor.execute('''
            INSERT INTO follows (flwer, flwee, start_date) VALUES (?, ?, DATE('now'))
        ''', (current_user_id, target_user_id))
        conn.commit()
        print("You are now following the user.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    return

def display_more_tweets(user_id):
    try:
        # Assuming the user wants to see more than the 3 most recent tweets
        cursor.execute('''
            SELECT tid, text FROM tweets WHERE writer = ? ORDER BY tdate DESC
        ''', (user_id,))
        tweets = cursor.fetchall()

        # Pagination logic for tweets
        page = 0
        while True:
            start_index = page * 5
            end_index = start_index + 5
            for tweet in tweets[start_index:end_index]:
                print(f"Tweet ID: {tweet[0]}, Tweet: {tweet[1]}")

            if end_index >= len(tweets):
                print("End of tweets.")
                return
            else:
                cont = input("Show more tweets? (y/n): ").strip().lower()
                if cont == 'y':
                    page += 1
                else:
                    return
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    return

def compose_tweet(usr):
    try:
        tweet_text = input("Compose your tweet (hashtags with #): ")
        hashtags = [word[1:] for word in tweet_text.split() if word.startswith("#")]
        current_time = datetime.datetime.now().strftime('%Y-%m-%d')

        # Get the next tweet ID
        cursor.execute('SELECT MAX(tid) FROM tweets')
        max_id = cursor.fetchone()[0]  # Fetchone returns a tuple, [0] gets the value
        tid = max_id + 1 if max_id else 1  # If the table is empty, start with 1

        # Insert tweet into tweets table
        tweet_insert_query = 'INSERT INTO tweets (tid, writer, tdate, text) VALUES (?, ?, ?, ?)'
        cursor.execute(tweet_insert_query, (tid, usr, current_time, tweet_text))

        # Insert hashtags into hashtags table and mentions table
        for hashtag in hashtags:
            # Ensure the hashtag is in the hashtags table
            cursor.execute('INSERT OR IGNORE INTO hashtags (term) VALUES (?)', (hashtag,))
            conn.commit()  # It's safe to commit here since hashtags table is independent

            # Insert into mentions table
            cursor.execute('INSERT INTO mentions (tid, term) VALUES (?, ?)', (tid, hashtag))
        
        # Final commit for tweet and mentions
        conn.commit()  

        print("Tweet posted successfully!")
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
        conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        conn.rollback()
    finally:
        user_interface(usr)  # Return to the main user interface function
    return

def list_followers(usr):
    try:
        query = '''
        SELECT usr, name FROM users
        WHERE usr IN (SELECT flwer FROM follows WHERE flwee = ?)
        '''
        cursor.execute(query, (usr,))
        followers = cursor.fetchall()

        # Display followers
        print("Your followers:")
        for idx, follower in enumerate(followers):
            print(f"{idx + 1}. {follower[1]} (User ID: {follower[0]})")

        # Handle follower selection
        selection = input("Select a follower to view more info, or type 'back' to return: ")
        if selection.lower() == 'back':
            return
        selected_idx = int(selection) - 1
        selected_usr = followers[selected_idx][0]

        # Fetch additional information about the follower
        num_tweets_query = 'SELECT COUNT(*) FROM tweets WHERE writer = ?'
        num_following_query = 'SELECT COUNT(*) FROM follows WHERE flwer = ?'
        num_followers_query = 'SELECT COUNT(*) FROM follows WHERE flwee = ?'
        recent_tweets_query = 'SELECT tid, text, tdate FROM tweets WHERE writer = ? ORDER BY tdate DESC LIMIT 3'

        cursor.execute(num_tweets_query, (selected_usr,))
        num_tweets = cursor.fetchone()[0]

        cursor.execute(num_following_query, (selected_usr,))
        num_following = cursor.fetchone()[0]

        cursor.execute(num_followers_query, (selected_usr,))
        num_followers = cursor.fetchone()[0]

        cursor.execute(recent_tweets_query, (selected_usr,))
        recent_tweets = cursor.fetchall()

        # Display the follower information
        print(f"User ID: {selected_usr}")
        print(f"Number of tweets: {num_tweets}")
        print(f"Following: {num_following}")
        print(f"Followers: {num_followers}")
        print("Most recent tweets:")
        for tweet in recent_tweets:
            print(f"Tweet ID: {tweet[0]}, Date: {tweet[2]}, Tweet: {tweet[1]}")

        # Handle tweet interaction
        action = input("Select a tweet to reply (R) / retweet (RT) or type 'follow' to follow this user: ")
        if action.lower() == "r":
            tweet_id = input("Enter the Tweet ID to reply to: ")
            if tweet_id.isdigit():
                compose_reply(int(tweet_id), usr)
            else:
                print("Invalid Tweet ID. Please enter a numeric value.")
        elif action.lower() == "rt":
            tweet_id = input("Enter the Tweet ID to retweet: ")
            if tweet_id.isdigit():
                retweet(int(tweet_id), usr)
            else:
                print("Invalid Tweet ID. Please enter a numeric value.")
        elif action.lower() == "follow":
            follow_user(selected_usr)
        else:
            print("Invalid action. Please enter 'R' to reply, 'RT' to retweet, or 'follow' to follow the user.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
        conn.rollback()
    except ValueError as e:
        print(f"A value error occurred: {e}")
    except IndexError as e:
        print(f"An index error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        user_interface(usr)  # Assuming this is the function to return to the user interface
    return

def logout():
    print("You have been logged out.")
    return

def display_tweets_for_user(user_id, page=0):
    try:
        offset = page * 5
        # Retrieve 5 tweets starting from the offset
        cursor.execute('''
            SELECT t.tid, t.text, t.tdate
			FROM tweets t
			JOIN follows f ON t.writer = f.flwee
			WHERE f.flwer = :user
			UNION
			SELECT r.tid, t.text, r.rdate
			FROM retweets r
			JOIN tweets t ON r.tid = t.tid
			JOIN follows f ON t.writer = f.flwee
			WHERE f.flwer = :user
			ORDER BY tdate DESC
            LIMIT 5 OFFSET ?
        ''', (user_id, offset))

        tweets = cursor.fetchall()
        if not tweets:
            if page == 0:
                print("You have no tweets to display.")
            else:
                print("No more tweets to display.")
            # Add an input here to allow the user to go back to the main menu
            input("Press any key to return to the main menu...")
            return  # This will exit the function and continue with the main loop

        for idx, tweet in enumerate(tweets, start=1):
            print(f"{idx}. {tweet[1]} (Date: {tweet[2]})")

        tweet_selection = input("Select a tweet number to view statistics, 'n' to see more tweets, or 'b' to go back: ")
        if tweet_selection.lower() == 'n':
            # Display next page of tweets
            display_tweets_for_user(user_id, page+1)
        elif tweet_selection.lower() == 'b':
            # User chooses to go back to the main menu
            return
        elif tweet_selection.isdigit() and 0 < int(tweet_selection) <= len(tweets):
            # Selected a tweet, now get tweet statistics and interact
            selected_tweet_id = tweets[int(tweet_selection) - 1][0]
            display_tweet_statistics(selected_tweet_id)
            interact_with_tweet(selected_tweet_id, user_id)
        else:
            print("Invalid selection. Please try again.")
            return

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    return

def display_tweet_statistics(tweet_id):
    try:
        # Retrieve tweet statistics
        cursor.execute('''
            SELECT COUNT(DISTINCT r.tid), COUNT(DISTINCT tw.tid)
            FROM tweets t
            LEFT JOIN retweets r ON t.tid = r.tid
            LEFT JOIN tweets tw ON t.tid = tw.replyto
            WHERE t.tid = ?
        ''', (tweet_id,))
        
        stats = cursor.fetchone()
        print(f"Retweets: {stats[0]}, Replies: {stats[1]}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    return

def interact_with_tweet(tweet_id, user_id):
    print("1. Reply to Tweet")
    print("2. Retweet")
    action = input("Choose an action (1-2) or press any other key to go back: ")
    if action == '1':
        compose_reply(tweet_id, user_id)
    elif action == '2':
        retweet(tweet_id, user_id)
    return

def compose_reply(tweet_id, user_id):
    reply_text = input("Type your reply (or type 'back' to return to the main menu): ")
    if reply_text.lower() == 'back':
        return
    try:
        # Get the next tweet ID for the reply
        cursor.execute('SELECT MAX(tid) FROM tweets')
        max_id = cursor.fetchone()[0]  # Fetchone returns a tuple, [0] gets the value
        reply_tid = max_id + 1 if max_id else 1  # If the table is empty, start with 1

        # Insert the reply into the tweets table, with reply_to field set to the original tweet's ID
        cursor.execute('''
            INSERT INTO tweets (tid, writer, tdate, text, replyto)
            VALUES (?, ?, datetime('now'), ?, ?)
        ''', (reply_tid, user_id, reply_text, tweet_id))
        conn.commit()
        print("Your reply was posted successfully.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        user_interface(user_id)  # Call the main menu function to return
    return

def retweet(tweet_id, user_id):
    # Confirm retweet action
    confirm = input("Press 'y' to retweet or 'back' to return to the main menu: ")
    if confirm.lower() == 'back':
        return
    elif confirm.lower() == 'y':
        try:
            # Insert the retweet into the retweets table
            cursor.execute('''
                INSERT INTO retweets (usr, tid, rdate)
                VALUES (?, ?, date('now'))
            ''', (user_id, tweet_id))
            conn.commit()
            print("The tweet was retweeted successfully.")
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            conn.rollback()
        finally:
            user_interface(user_id)
    return

def user_interface(user_id):
    while True:
        print("\n--- Welcome to the Twitter Clone! ---")        
        print("\nOptions:")
        print("d - Display tweets")
        print("s - Search for tweets")
        print("u - Search for users")
        print("c - Compose a tweet")
        print("l - List followers")
        print("q - Logout")
        
        choice = input("Choose an option: ").lower()
        
        if choice == "s":
            search_tweets(user_id)
        elif choice == "u":
            search_users(user_id)
        elif choice == "d":
            display_tweets_for_user(user_id)
        elif choice == "c":
            compose_tweet(user_id)
        elif choice == "l":
            list_followers(user_id)
        elif choice == "q":
            logout()
            return
        else:
            print("Invalid option, please try again.")
    return

# Main loop
def main():
    while True:
        print("\n1. Login\n2. Register\n3. Exit")
        user_choice = input("Choose an option: ")
        
        if user_choice == "1":
            user_id = login()
            if user_id:
                user_interface(user_id)
        elif user_choice == "2":
            register()
        elif user_choice == "3":
            print("Exiting the program...")
            exit()
        else:
            print("Invalid input, please try again.")

if __name__ == "__main__":
    main()
