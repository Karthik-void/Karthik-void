import streamlit as st
import pandas as pd
import datetime
from collections import defaultdict
import random
import time
import os
import requests
from openai import OpenAI

st.set_page_config(page_title="AI Study Planner", layout="centered")

# ---- HEADER ----
st.title("📚 AI-Based Study Planner (Advanced)")
st.markdown("Create a smart, personalized study schedule with AI enhancements.")

# ---- USER INPUTS ----
st.header("1. Student Information")
name = st.text_input("Enter your name:")
available_hours = st.slider("Average daily study hours:", 1, 10, 3)
exam_date = st.date_input("Select exam date:", datetime.date.today() + datetime.timedelta(days=30))

# ---- SUBJECT INPUT ----
st.header("2. Subject Preferences")
subjects = st.text_area("Enter subjects (comma-separated):", "Math, Science, History")
subject_list = [s.strip() for s in subjects.split(',') if s.strip() != '']

# Difficulty scale input
st.subheader("Rate Difficulty (1 - Easy to 5 - Hard)")
difficulty_dict = {}
for subject in subject_list:
    difficulty_dict[subject] = st.slider(f"{subject} difficulty:", 1, 5, 3)

# ---- SCHEDULE GENERATION ----
def generate_schedule(subjects, difficulty, available_hours, exam_date):
    total_days = (exam_date - datetime.date.today()).days
    total_available_hours = total_days * available_hours
    total_weight = sum(difficulty.values())
    if total_weight == 0:
        total_weight = 1
    hours_per_subject = {
        subject: round((difficulty[subject] / total_weight) * total_available_hours, 1)
        for subject in subjects
    }
    schedule = defaultdict(list)
    current_day = datetime.date.today()
    day = 0
    while day < total_days:
        daily_hours = available_hours
        today_plan = []
        for subject in subjects:
            if hours_per_subject[subject] > 0:
                allocated = min(1.0, hours_per_subject[subject], daily_hours)
                if allocated > 0:
                    today_plan.append((subject, allocated))
                    hours_per_subject[subject] -= allocated
                    daily_hours -= allocated
        if today_plan:
            schedule[current_day + datetime.timedelta(days=day)] = today_plan
        # Add review tasks (spaced repetition)
        review_day = current_day + datetime.timedelta(days=day + 2)
        for subject, hours in today_plan:
            schedule[review_day].append((f"Review {subject}", round(hours / 2, 1)))
        day += 1
    return schedule

# ---- MAIN BUTTON ----
if st.button("Generate Study Plan"):
    if name and subject_list:
        plan = generate_schedule(subject_list, difficulty_dict, available_hours, exam_date)
        st.success(f"Study plan generated for {name}!")
        
        st.header("3. Your Study Plan")
        plan_list = []
        for date, tasks in plan.items():
            st.subheader(f"📅 {date.strftime('%A, %d %B %Y')}")
            for subject, hours in tasks:
                st.write(f"- *{subject}*: {hours} hour(s)")
                plan_list.append({"Date": date, "Subject": subject, "Hours": hours})
        df_plan = pd.DataFrame(plan_list)
        csv = df_plan.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Study Plan as CSV", csv, "study_plan.csv", "text/csv")

        # ---- PROGRESS TRACKER ----
        st.header("4. Mark Today's Progress")
        today = datetime.date.today()
        if today in plan:
            st.subheader(f"✅ Tasks for {today.strftime('%A, %d %B %Y')}")
            for subject, hours in plan[today]:
                st.checkbox(f"{subject} - {hours} hour(s)", key=f"{subject}_{today}")

        # ---- VISUALIZATION ----
        st.header("5. Summary Chart")
        if not df_plan.empty and "Subject" in df_plan.columns and "Hours" in df_plan.columns:
            summary_df = df_plan.groupby("Subject")["Hours"].sum().reset_index()
            st.bar_chart(summary_df.set_index("Subject"))
        else:
            st.warning("No data available for chart. Please make sure your subjects and difficulty ratings are set correctly.")

        # ---- STUDY TIPS ----
        st.header("6. 📌 AI-Generated Study Tips")
        tips = [
            "📌 Set short-term and long-term goals to stay motivated.",
            "📌 Use the Pomodoro technique: 25 minutes focused study, 5 minutes break.",
            "📌 Review your notes within 24 hours of learning for better retention.",
            "📌 Practice with previous years’ question papers regularly.",
            "📌 Prioritize hard subjects earlier in the day when you're more focused.",
            "📌 Sleep well—minimum 7–8 hours helps with memory and concentration.",
            "📌 Avoid multitasking—focus on one subject at a time."
        ]
        st.info(random.choice(tips))

        # ---- NOTIFICATION & REMINDER ----
        st.header("7. ⏰ Notification & Reminders")
        st.write("This app simulates a reminder system. For actual reminders, use phone/calendar apps with the study plan.")
        upcoming = [(d, t) for d, t in plan.items() if d >= today][:3]
        for date, tasks in upcoming:
            st.subheader(f"🔔 Reminder: {date.strftime('%A, %d %B %Y')}")
            for subject, hours in tasks:
                st.write(f"Don't forget to study *{subject}* for {hours} hour(s)")

        # ---- PRODUCTIVITY CHECK ----
        st.header("8. 📈 Productivity Tracker")
        actual_hours = st.number_input("How many hours did you actually study today?", min_value=0.0, step=0.5)
        if actual_hours:
            st.success(f"Productivity today: {round((actual_hours / available_hours)*100)}%")

        # ---- MILESTONE ALERT ----
        st.header("9. 🎯 Milestones")
        percent_complete = (df_plan['Hours'].cumsum().iloc[-1] / df_plan['Hours'].sum()) * 100
        st.progress(min(int(percent_complete), 100))

        # ---- RESOURCE SUGGESTIONS ----
        st.header("10. 📚 Resource Suggestions")
        API_KEY = st.secrets.get("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY")

        if 'favorites' not in st.session_state:
            st.session_state['favorites'] = []

        def save_favorite(resource):
            if resource not in st.session_state['favorites']:
                st.session_state['favorites'].append(resource)
                st.success("Resource saved to favorites!")

        for subject in subject_list:
            st.subheader(f"Resources for {subject}")
            if API_KEY:
                search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={subject}+tutorial&type=playlist&key={API_KEY}&maxResults=1"
                try:
                    res = requests.get(search_url)
                    if res.status_code == 200:
                        data = res.json()
                        if data["items"]:
                            item = data["items"][0]
                            title = item["snippet"]["title"]
                            playlist_id = item["id"]["playlistId"]
                            link = f"https://www.youtube.com/playlist?list={playlist_id}"
                            st.markdown(f"▶ [YouTube Playlist: {title}]({link})")
                            if st.button(f"Save YouTube Playlist for {subject}", key=f"yt_{subject}"):
                                save_favorite({"type": "YouTube Playlist", "subject": subject, "title": title, "link": link})
                        else:
                            st.warning(f"No YouTube playlist found for {subject}")
                    else:
                        st.error(f"Failed to fetch YouTube data for {subject}")
                except Exception as e:
                    st.error(f"Error fetching YouTube playlist for {subject}: {e}")
            articles = [
                {
                    "title": f"Introduction to {subject}",
                    "link": f"https://en.wikipedia.org/wiki/{subject}"
                },
                {
                    "title": f"Top {subject} Study Tips",
                    "link": f"https://www.study.com/academy/topic/{subject.replace(' ', '-').lower()}.html"
                }
            ]
            st.write("📄 Articles:")
            for idx, article in enumerate(articles):
                st.markdown(f"- [{article['title']}]({article['link']})")
                if st.button(f"Save Article {idx+1} for {subject}", key=f"article_{subject}_{idx}"):
                    save_favorite({"type": "Article", "subject": subject, "title": article['title'], "link": article['link']})

        if st.session_state['favorites']:
            st.header("⭐ Your Favorite Resources")
            for fav in st.session_state['favorites']:
                st.markdown(f"- *{fav['subject']}* | {fav['type']} : [{fav['title']}]({fav['link']})")
        else:
            st.info("You have no favorite resources saved yet.")

if __name__ == "__main__":
    pass
