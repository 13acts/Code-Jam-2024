import random

import discord
from discord.ui import Button, View
from utils.quiz import fetch_categories, learn_more_url

VOTING_TIME = 10


class VotingView(View):
    """Topic voting message. Subclasses `View`.

    Attributes
    ----------
    user_votes : dict
        Collection of topics and their corresponding votes.
    topic_ids : dict
        A topic pool as returned by `utils.quiz.fetch_categories`.
    cancel_button
        A `CancelButton` instance corresponding to a cancel button in this voting UI.

    """

    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.user_votes = {}
        self.topic_ids = fetch_categories()
        self.message: discord.Message = None

        for topic in [*random.sample(list(self.topic_ids.keys()), 3), "Random"]:
            self.add_item(TopicButton(label=topic, value=topic, voting_view=self, row=0))

        for count in [5, 10, 15]:
            self.add_item(NumQuestionButton(label=f"{count} Questions", count=count, voting_view=self, row=1))

        self.cancel_button = CancelButton(voting_view=self, row=2)
        self.add_item(self.cancel_button)

    async def on_timeout(self) -> None:
        """After timeout, select topic and number of questions for the coming quizzes."""

        def determine_winner(buttons: TopicButton | NumQuestionButton) -> str:
            """Determine the winning selection from the buttons."""
            counts = {child.value: child.votes for child in buttons}
            max_votes = max(counts.values())
            winners = [value for value, votes in counts.items() if votes == max_votes]
            return random.choice(winners)  # noqa: S311

        def update_button(buttons: TopicButton | NumQuestionButton, selected: str) -> None:
            """Update the original message to highlight the selected options and disable buttons."""
            for child in buttons:
                if child.value == selected:
                    child.style = discord.ButtonStyle.success
                child.disabled = True

        # Separate TopicButton and NumQuestionButton and CancelButton
        topic_buttons = [child for child in self.children if isinstance(child, TopicButton)]
        question_buttons = [child for child in self.children if isinstance(child, NumQuestionButton)]
        cancel_button = next(child for child in self.children if isinstance(child, CancelButton))

        # Determine the final selection
        if cancel_button.is_cancelled:
            return False

        # If Random, display the Random button as pressed while still send the random topic
        most_vote_topic = determine_winner(topic_buttons)
        if most_vote_topic == "Random":  # noqa: SIM108
            selected_topic = random.choice(list(self.topic_ids.keys()))  # noqa: S311
        else:
            selected_topic = most_vote_topic

        selected_number = determine_winner(question_buttons)

        # Update final buttons
        update_button(topic_buttons, most_vote_topic)
        update_button(question_buttons, selected_number)
        self.remove_item(self.cancel_button)

        # Edit bot's message
        result_message = f"Started **{selected_number} questions** on the topic: **{selected_topic}**"
        await self.message.edit(content=result_message, view=self)

        # Return results
        return (selected_number, selected_topic)


class BaseVotingButton(Button):
    """Base for voting button layouts. Subclasses `Button`.

    Parameters
    ----------
    label : str
        Button label.
    value : int | str
        Value registered by button press.
    voting_view
        The `VotingView` instance this button is added to.
    votes : int
        Number of votes for this button (topic).
    row : int
        The row this button belongs to.
    style
        An instance of `discord.ButtonStyle`.

    Attributes
    ----------
    label_text : str
        Button label.
    value : int | str
        Value registered by button press.
    voting_view
        The `VotingView` instance this button is added to.
    votes : int
        Number of votes for this button (topic).

    """

    def __init__(
        self,
        label: str,
        value: int | str,
        voting_view: VotingView,
        row: int,
        style: discord.ButtonStyle,
    ) -> None:
        super().__init__(label=f"{label} (0)", style=style, row=row)
        self.label_text = label
        self.value = value
        self.votes = 0
        self.voting_view = voting_view

    async def callback(self, interaction: discord.Interaction) -> None:
        """Register and update buttons.

        Parameters
        ----------
        interaction
            The interaction that represents this command invocation.

        """
        user_id = interaction.user.id
        previous_selection = self.voting_view.user_votes.get(user_id, {})

        # Determine the type of the current button (topic or question count)
        is_topic_button = isinstance(self, TopicButton)
        previous_value = previous_selection.get("topic" if is_topic_button else "count")

        # If user already voted, remove their vote from the previous selection
        if previous_value is not None:
            for child in self.voting_view.children:
                if isinstance(child, BaseVotingButton) and child.value == previous_value:
                    child.votes -= 1
                    child.label = f"{child.label_text} ({child.votes})"
                    break

        # Register the new vote
        previous_selection["topic" if is_topic_button else "count"] = self.value
        self.voting_view.user_votes[user_id] = previous_selection
        self.votes += 1
        self.label = f"{self.label_text} ({self.votes})"

        # Update Cancel button
        cancel_button = self.voting_view.cancel_button
        cancel_button.label = f"Cancel ({cancel_button.votes}/{len(self.voting_view.user_votes)})"

        # Update the view
        await interaction.response.edit_message(view=self.voting_view)


class TopicButton(BaseVotingButton):
    """Topic select button layouts. Subclasses `BaseVotingButton`.

    Parameters
    ----------
    label : str
        Button label.
    value : int | str
        Value registered by button press.
    voting_view
        The `VotingView` instance this button is added to.
    row : int
        The row this button belongs to.

    """

    def __init__(self, label: str, value: str, voting_view: VotingView, row: int) -> None:
        super().__init__(label=label, value=value, voting_view=voting_view, row=row, style=discord.ButtonStyle.primary)


class NumQuestionButton(BaseVotingButton):
    """Button for selecting the number of questions.

    Parameters
    ----------
    label : str
        Button label.
    count : int
        Number of questions.
    voting_view
        The `VotingView` instance this button is added to.
    row : int
        The row this button belongs to.

    """

    def __init__(self, label: str, count: int, voting_view: VotingView, row: int) -> None:
        super().__init__(
            label=label,
            value=count,
            voting_view=voting_view,
            row=row,
            style=discord.ButtonStyle.secondary,
        )


class QuestionView(View):
    """Each question in the quiz. Subclasses `View`.

    Parameters
    ----------
    i : int
        Question index.
    question : str
        The question.
    correct : str
        Correct answer to question.
    incorrects : list
        Collection of incorrect answers.
    voting_view
        The `VotingView` instance this button is added to.
    type : str
        Question type.

    Attributes
    ----------
    user_answers : dict
        A dictionary corresponding to users and answers.
    i : int
        Question index.
    question : str
        The question.
    correct : str
        Correct answer to question.
    incorrects : list
        Collection of incorrect answers.
    url : str
        An URL as returned by `utils.wiki.learn_more_url`.

    """

    def __init__(self, i: int, question: str, correct: str, incorrects: list, type: str) -> None:
        super().__init__(timeout=None)
        self.user_answers = {}
        self.i = i
        self.question = question
        self.correct = correct
        self.incorrects = incorrects
        self.url = learn_more_url(self.question)
        self.message: discord.Message = None

        if type == "multiple":
            answers = [*incorrects, correct]
            random.shuffle(answers)
        elif type == "boolean":
            answers = ["True", "False"]

        for answer in answers:
            self.add_item(AnswerButton(label=answer, question_view=self))

    async def on_timeout(self) -> list:
        """After timeout, highlight correct answer.

        Returns
        -------
        list
            IDs of users who answered correctly.

        """
        # Highlight correct answer, disable all buttons
        for child in self.children:
            if child.label == self.correct:
                child.style = discord.ButtonStyle.success
            child.disabled = True

        # Add Learn More button
        self.add_item(LearnMoreButton(url=self.url))

        try:
            await self.message.edit(content=f"### {self.i}) {self.question}", view=self)
        except discord.HTTPException as e:
            print(f"HTTPException while editing message: {e}")

        # Return correct users
        return [id for id in self.user_answers if self.user_answers[id] == self.correct]


class AnswerButton(Button):
    """Button for selecting the answer. Subclasses `Button`.

    Parameters
    ----------
    label : str
        Button label.
    question_view
        The `QuestionView` instance this button is added to.

    Attributes
    ----------
    question_view
        The `QuestionView` instance this button is added to.

    """

    def __init__(self, label: str, question_view: QuestionView) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.question_view = question_view

    async def callback(self, interaction: discord.Interaction) -> None:
        """Register user's answer."""
        user_id = interaction.user.id
        self.question_view.user_answers[user_id] = self.label
        await interaction.response.edit_message(view=self.question_view)


class LearnMoreButton(Button):
    """Button to open wiki page regarding the question. Subclasses `Button`.

    Parameters
    ----------
    url : str
        An url as returned by `utils.wiki.learn_more_url`.

    """

    def __init__(self, url: str) -> None:
        super().__init__(label="Learn more", url=url, style=discord.ButtonStyle.secondary)


class CancelButton(Button):
    """Cancel the quiz. Only available during voting phase. Subclasses `Button`.

    Parameters
    ----------
    voting_view
        The `VotingView` instance this button is added to.
    row : int
        The row this button belongs to.

    Attributes
    ----------
    label_text : str
        Label of cancel button. "Cancel" by default.
    votes : int
        Number of cancel votes.
    voting_view
        The `VotingView` instance this button is added to.
    is_cancelled : bool
        Indicates cancel status.

    """

    def __init__(self, voting_view: VotingView, row: int) -> None:
        super().__init__(label="Cancel", row=row, style=discord.ButtonStyle.red)
        self.votes = 0
        self.voting_view = voting_view
        self.is_cancelled = False

    async def callback(self, interaction: discord.Interaction) -> None:
        """Register and update buttons."""
        user_id = interaction.user.id
        user_selections = self.voting_view.user_votes.get(user_id, {})
        cancel_value = user_selections.get("cancel", False)

        # Register the new vote
        user_selections["cancel"] = not (cancel_value)
        self.voting_view.user_votes[user_id] = user_selections
        self.votes += 1 if not (cancel_value) else -1
        self.label = f"Cancel ({self.votes}/{len(self.voting_view.user_votes)})"

        # Determine cancel state
        self.is_cancelled = False if self.votes == 0 else self.votes > len(self.voting_view.user_votes) / 2

        # Update the view
        await interaction.response.edit_message(view=self.voting_view)


def voting_time() -> int:
    """Return global variable for use in quiz.py."""
    return VOTING_TIME
