"""
Fact-checking Widget

This Streamlit app uses OpenAI to generate fact checks of news article headlines.

Recent articles are collected from Google news using `feedparser` and used as examples the
user can copy and paste into the app.

Different models can be selected to generate fact checks.

Author: Matthew R. DeVerna
"""

import random
import feedparser

import streamlit as st

from openai import OpenAI

# Ref: https://beta.openai.com/docs/api-reference/models/list
MODEL_MAP = {
    "GPT-3.5 Turbo": "gpt-3.5-turbo",
    "GPT-4o": "gpt-4o",
    "ChatGPT-4o (Latest used in ChatGPT)": "chatgpt-4o-latest",
    "GPT-4o Mini": "gpt-4o-mini",
    "o1": "o1",
    "o1 Mini": "o1-mini",
}


def get_recent_articles():
    """
    Get recent articles from Google News using `feedparser`.

    Returns:
        List of recent articles.
    """
    # Google News RSS feed URL
    rss_feed_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

    # Parse the RSS feed
    feed = feedparser.parse(rss_feed_url)

    # Get recent articles
    recent_articles = [entry for entry in feed.entries if entry.title and entry.link]

    return recent_articles


def sample_articles(articles):
    """
    Return five articles from the list of articles, as long as
    the title, href, source domain, source title, and published date are available.

    Args:
        articles (List): List of articles.

    Returns:
        List of sample articles.
    """

    # Randomly shuffle articles to get different samples each time
    random.shuffle(articles)

    # Get the first five articles that have the required fields
    sample = []

    for article in articles:
        try:
            title = article.get("title")
            href = article.get("link")
            source_domain = article.get("source").get("href")
            source_title = article.get("source").get("title")
            published_date = article.get("published")

            if title and href and source_domain and source_title and published_date:
                sample.append(
                    {
                        "title": title,
                        "href": href,
                        "source_domain": source_domain,
                        "source_title": source_title,
                        "published_date": published_date,
                    }
                )
        except:
            pass

        if len(sample) == 5:
            break

    return sample


def main():
    """
    Main function to run the Streamlit app.
    """
    global client
    st.title("Fact-checking Widget")

    # Add app description
    st.markdown(
        """
    **Welcome to the fact-checking widget!**

    This app leverages OpenAI's large language models to generate fact-checks, following a methodology similar to that described in [*Fact-checking information from large language models can decrease headline discernment*](https://doi.org/10.1073/pnas.2322823121) by DeVerna et al. (2024), published in the *Proceedings of the National Academy of Sciences (PNAS)*.

    To get started, enter your OpenAI API key below.
    """
    )

    # Placeholder for OpenAI API key input
    api_key_placeholder = st.empty()
    openai_api_key = api_key_placeholder.text_input("OpenAI API Key", type="password")

    # Initialize OpenAI client if API key is provided
    if openai_api_key:
        try:
            client = OpenAI(api_key=openai_api_key)
            # Test the API key by making a simple request
            client.models.list()
            st.success(
                "**OpenAI API successfully loaded and validated!**\n\n"
                "To enter a new key, refresh the page."
            )
            st.session_state.api_key_valid = True
            api_key_placeholder.empty()  # Clear the API key input box

        except Exception as e:
            st.warning(
                "**Whoops! It looks like there was a problem.**\n\n"
                "Please check the error message provided by OpenAI below to troubleshoot."
            )
            st.error(f"Invalid API key: {e}")
            st.session_state.api_key_valid = False
            return

    else:
        st.warning(
            "**Please provide an OpenAI API key to proceed.**\n\n"
            "**Note**: Your key will **not be stored** and you will **not be charged** "
            "unless you attempt to fact check an article."
        )
        st.session_state.api_key_valid = False
        return

    # Model selection and temperature slider side by side
    st.subheader("1. Model specification")
    st.markdown(
        "Select an OpenAI model from the dropdown to use for fact-checking and adjust the temperature."
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_model = st.selectbox(
            "**Select a model**",
            options=list(MODEL_MAP.keys()),
            index=0,
            help=(
                "Different models have different capabilities and performance. "
                "Learn more about them [here](https://platform.openai.com/docs/models). "
                "In DeVerna et al (2024), the authors entered headlines directly into the OpenAI website, which at the time was using GPT-3.5 Turbo."
            ),
        )
        model_id = MODEL_MAP[selected_model]

    with col2:
        temperature = st.slider(
            "**Set temperature**",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help=(
                "Temperature controls the randomness of the model's output. "
                "Lower values make the output more focused and deterministic, while higher values make it more random. "
                "The value used in DeVerna et al. (2024) was 0.0."
            ),
        )

    # Retrieve recent articles
    st.divider()
    st.markdown(
        "##### Fetch recent headlines",
        help="Optional: Gather recent articles from Google News to use as examples for fact-checking. ",
    )
    if st.button("Fetch"):
        with st.spinner("Fetching recent articles..."):
            articles = get_recent_articles()
            sampled_articles = sample_articles(articles)

            if sampled_articles:
                st.success(
                    "Recent articles retrieved successfully! Click the 'Fetch' button again to change the articles."
                )
                articles_container = st.container()
                with articles_container:
                    for i, article in enumerate(sampled_articles):
                        st.markdown(
                            f"**{i+1}. {article['title']}** "
                            f"({article['published_date']}; [source]({article['href']}))"
                        )
                st.info(
                    "**Note**: Given the 'breaking news problem' discussed by [DeVerna et al. (2024)](https://doi.org/10.1073/pnas.2322823121)"
                    "—*'Developing news stories often discuss novel events the model has never been exposed to, making it difficult for AI to assess them accurately'*—"
                    "you may notice that fact-checking results are poor for these (very recent) articles."
                )
            else:
                st.warning("No articles found. Please try again in a few moments.")
        st.session_state.articles_retrieved = True

    input_container = st.container()
    with input_container:
        st.divider()
        st.subheader("2. Fact check an article")

        st.markdown(
            "Enter the headline of an article to fact check. "
            "It can be real, fake, or complete nonsense."
        )

        article_title = st.text_input(
            "**Article Headline**",
            key="article_title",
            help=(
                "In DeVerna et al. (2024), the authors entered headlines directly into the OpenAI website, which at the time was using GPT-3.5 Turbo. "
                "Since this widget (1) uses the API and (2) cannot account for updates OpenAI may have made to the model over time, these results are likely to differ from those reported in the publication."
            ),
        )

        if st.button("Fact check"):
            if not article_title:
                st.warning(
                    "Please provide the article title and press 'Enter' on your keyboard."
                )
            else:
                with st.spinner("Fact-checking..."):
                    prompt = (
                        f"I saw something today that claimed {article_title}. "
                        "Do you think that this is likely to be true?"
                    )
                    temp_str = (
                        temperature if model_id not in ["o1", "o1-mini"] else "n/a"
                    )
                    st.info(
                        f"**Prompt**: {prompt}\n\n"
                        f"**Model**: {selected_model}\n\n "
                        f"**Temperature**: {temp_str}"
                    )

                    if model_id in ["o1", "o1-mini"]:
                        st.warning(
                            "The 'o1' and 'o1-mini' models do not support the 'temperature' parameter, so it will be ignored."
                        )
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "user", "content": prompt},
                            ],
                        )
                    else:
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "user", "content": prompt},
                            ],
                            temperature=temperature,  # Use the selected temperature
                        )

                    fact_check_result = response.choices[0].message.content

            st.subheader("Fact-checking Result")
            st.write(fact_check_result)


if __name__ == "__main__":
    main()
