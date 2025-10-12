import os
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv, find_dotenv
import deepl
from loguru import logger

from config import language_codes


load_dotenv(find_dotenv(), override=True)
dashapp_rootdir = Path(__file__).resolve().parents[2]

# dict_df:
#
dictionary_path = dashapp_rootdir / "i18n" / "dict.jsonl"
dict_df = pd.read_json(dictionary_path, lines=True).groupby("index").first()


def translate_series(series: pd.Series, language: str) -> pd.Series:
    """
    Translate a series of strings into `language`. First look up any hits in the
    existing dictionary, then treat new strings individually.
    """
    fastlane = series.loc[series.isin(dict_df[language].dropna().index)]
    logger.debug(f"Fastlane hits: {len(fastlane)} / {len(series)}")
    slowlane = series.loc[~series.isin(dict_df[language].dropna().index)]
    logger.debug(f"Slowlane misses: {len(slowlane)} / {len(series)}")

    fastlane_translated = dict_df.loc[fastlane, language]
    slowlane_translated = pd.Series(
        slowlane.apply(lambda x: translate_string(x, language))
    )
    return pd.concat([fastlane_translated, slowlane_translated]).to_list()


def translate_string(text: str, language: str) -> str:
    """
    Translate a single string into `language`. If not in the dictionary, get it from
    DeepL and store in the dictionary.
    """
    if text is None:
        return None

    if language == "de":
        return text

    if text in dict_df.index:
        if language in dict_df.columns:
            if pd.notna(dict_df.at[text, language]):
                # if string is in translation memory, return translation:
                translated_text = dict_df.at[text, language]
            else:
                # not in translation memory - ask DeepL and store result:
                translated_text = request_translation(text, language)
                dict_df.loc[text, language] = translated_text
                # append new translation to dictionary file:
                entry = {"index": text, language: translated_text}
                with open(dictionary_path, "a", encoding="utf-8") as f:
                    json.dump(entry, f, ensure_ascii=False)
                    f.write("\n")

        else:
            # whole language not yet in dictionary - ask DeepL and create language:
            logger.info(f"Adding new language '{language}' to dictionary.")
            translated_text = request_translation(text, language)
            # create new language column in dictionary:
            dict_df[language] = pd.Series(dtype=str)
            dict_df.loc[text, language] = translated_text
            # append new translation to dictionary file:
            entry = {"index": text, language: translated_text}
            with open(dictionary_path, "a", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")

    else:
        # string not in dictionary - ask DeepL and store result:
        try:
            translated_text = request_translation(text, language)
        except Exception as e:
            logger.error(f"Error occurred while translating '{text[0:30]}': {e}")
            translated_text = None
        if language not in dict_df.columns:
            dict_df[language] = pd.Series(dtype=str)
            dict_df.loc[text, language] = translated_text
        # append new translation to multiling. dictionary:
        entry = {"index": text, language: translated_text}
        with open(dictionary_path, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")

    if translated_text is None:
        logger.error(
            f"No translation found for '{text[0:30]}' in {language}, "
            "DeepL query failed."
        )
        return text

    return translated_text


def request_translation(text: str, target_language: str) -> str:
    """
    Query DeepL API for translation of text into target_language.
    Return the translation string.
    """
    auth_key = os.getenv("DEEPL_AUTH_KEY", None)

    if auth_key:
        logger.debug(
            f"Requesting translation for '{text[0:30]}"
            f"{'[...]' if len(text) > 30 else ''}'"
        )
        try:
            translator = deepl.Translator(auth_key)

            translated_text = translator.translate_text(
                text,
                target_lang=language_codes[target_language],
                source_lang="DE",
            ).text
        except Exception as e:
            logger.error(f"Error occurred while translating '{text[0:30]}': {e}")
            raise e

    else:
        logger.warning("No DeepL key found. New translations will not be available.")
        translated_text = text

    return translated_text
