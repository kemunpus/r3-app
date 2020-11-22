""" Logics """

import datetime
import json
import random

from django.http import Http404

from .models import MAX_MEDIA_COUNT, Media, Temp


def prep(logic):
    """Logicの準備をします.

    implementで指定されている情報に基づいて個別のprep実装を呼び出します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.

    Raises:
        Http404: implementに処理可能なLogicの名前がない場合.
    """

    # 結果のリストを空にしておきます.
    logic.media_list = ""
    logic.media_count = 0
    logic.state = ""

    # 一回保存しておきます.
    logic.save()

    # logicで指定されている実装を呼び出します.
    if logic.implement == "media":
        media_prep(logic)

    elif logic.implement == "text":
        text_prep(logic)

    elif logic.implement == "blank":
        blank_prep(logic)

    else:
        # 知らないLogicの名前が指定されたらエラーです.
        raise Http404

    # 結果を保存して終了です.
    logic.save()


def get_content(trial, seq):
    """表示するデータを決定します.

    implementで指定されている情報に基づいて個別のget_content実装を呼び出します.

    Args:
        trial (Trial): 実行中のTrialのインスタンス.
        seq (int): 要求しているデータの連番.

    Raises:
        Http404: 該当するデータが見つからなかった場合.

    Returns:
        (Json) 表示すべきデータの型とURLが示されたJsonデータ.
    """

    # Trialに結び付けられているLogicを取得します.
    logic = trial.logic

    # 指定されているget_contentを呼びだします.
    if logic.implement == "media":
        return media_get_content(trial, seq)

    elif logic.implement == "text":
        return text_get_content(trial, seq)

    elif logic.implement == "blank":
        return blank_get_content(trial, seq)

    # 知らないLogicの名前が指定されたらエラーです.
    raise Http404


def add_state(logic, message):
    """logicのstateに日時情報を前置してメッセージを追記します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
        message (str): 追記したいメッセージ.
    """

    # 新しい行を追記します.
    logic.state += "{} {}\n".format(str(datetime.datetime.today()), message)

    # 結果を書き込みます.
    logic.save()


def media_prep(logic):
    """Mediaを処理するLogicを準備します.

    指定された条件に合致するMediaを選択して保存しておきます.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
    """

    # 実行開始の情報をstateに書いておきます.
    add_state(logic, "media_prep started.")

    # 表示対象として指定されている拡張子のリストを取得します.
    ext_list = logic.media_ext.split()
    logic.media_ext = " ".join(map(str, ext_list))

    # 表示対象として指定されているタグのリストを取得します.
    tag_list = logic.media_tag.split()
    logic.media_tag = " ".join(map(str, tag_list))

    # 結果のMediaの主キーのリストを保持する空の配列を準備しておきます.
    media_list = []

    # 対象となるMediaをすべて新しい順に取得します.
    # 本来は"updated"を使うべきですが、Mongo(Cosmos)でエラーになるのでidで近似しています...
    media_all = Media.objects.all().order_by("id").reverse()

    # すべてのMediaを順番に処理していきます.
    for media in media_all:

        # 拡張子がtxtの場合はこのLogicでは処理しません.
        if media.ext == "txt":
            continue

        # 拡張子が条件に合致しているかチェックします.
        if ("*" in ext_list) or (media.ext in ext_list):
            matched = False

            # タグをチェックします.
            if "*" in tag_list:

                # タグが*で指定されているのならそのMediaは採用です.
                matched = True

            else:

                # Mediaのタグがリストに含まれているかを確認します.
                media_tag_list = media.tag.split()

                if not set(media_tag_list).isdisjoint(tag_list):

                    # 含まれていればそのMediaは採用です.
                    matched = True

            # Mediaが採用された場合の処理です.
            if matched:

                # 結果リストがいっぱいだったらもう追加しません.
                if len(media_list) >= MAX_MEDIA_COUNT:
                    break

                # 結果リストに追記します.
                media_list.append(media.id)

    # shuffleが指定されていれば結果のリストをシャッフルします.
    if logic.media_order == "shuffle":
        random.shuffle(media_list)

    # リストを空白区切りの文字列に展開します.
    media_list_str = " ".join(map(str, media_list))

    # 書き込む値としてセットします.
    logic.media_list = media_list_str

    # 採用されたMediaの個数もセットします.
    logic.media_count = len(media_list)

    # 実行終了の情報をstateに書いておきます.
    add_state(logic, "media_prep finished.")


def media_get_content(trial, seq):
    """media_prep()で準備された結果に基づいて表示すべきMediaを決定します.

    指定された連番に合致するMediaを返却します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
        seq (int): 要求しているメディアの連番.

    Raises:
        Http404: 該当するMediaが見つからなかった場合.

    Returns:
        (Json) メディアの型とURLが示されたJsonデータ.
    """

    # 実行中のTrialに結び付けられているLogicを取得します.
    logic = trial.logic

    # そのLogicが持っているMediaのリストを取得します.
    media_list = logic.media_list.split()
    media_count = len(media_list)

    # 表示すべきデータが一個もない場合はエラーにはせずにメッセージを出すようにします.
    if media_count == 0:
        return json.dumps({"type": "txt", "data": "No data to show"})

    # seq番目のMediaをとってきます.
    media_index = int(seq) % media_count
    media = Media.objects.get(pk=media_list[media_index])

    # Mediaが無事に取れた場合にはjsonを返します.
    if media:
        return json.dumps({"type": media.ext, "data": media.content.url})

    # Mediaが見つからなかった場合は404を返します.
    raise Http404


# Tempにデータを保持するための名前です.
TEXT_LOGIC_NAME = "text-logic-cache:{}"


def text_prep(logic):
    """テキストを表示するLogicを準備します.

    texts.py で静的に定義されたテキストの配列を準備します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
    """

    # 実行開始の情報をstateに書いておきます.
    add_state(logic, "text_prep started.")

    # テキストリストをクリアします.
    text_list = []

    # 表示対象として指定されているタグのリストを取得します.
    tag_list = logic.media_tag.split()
    logic.media_tag = " ".join(map(str, tag_list))

    # 対象となるMediaをすべて取得します.
    media_all = Media.objects.all()

    # すべてのMediaを順番に処理していきます.
    for media in media_all:

        # 拡張子をチェックします.
        if media.ext == "txt":

            # タグがリストに含まれているかを確認します.
            media_tag_list = media.tag.split()

            if not set(media_tag_list).isdisjoint(tag_list):

                # 読み込んでテキストのリストに追記します.
                with media.content.open(mode="rb") as text_file:
                    lines = text_file.read().decode("utf-8").splitlines()
                    text_file.close()
                    text_list.extend(lines)

    # インデックスを保持するリストを作成します.
    index_list = list(range(len(text_list)))

    # インデックスをシャッフルします.
    if logic.media_order == "shuffle":
        random.shuffle(index_list)

    # リストに書き込む最大数を計算します.
    max_index = min(len(index_list), MAX_MEDIA_COUNT)

    # リストを空白区切りの文字列に展開します.
    media_list_str = " ".join(map(str, index_list[:max_index]))

    # 採用されたMediaのリストをセットします.
    logic.media_list = media_list_str

    # 採用されたMediaの個数もセットします.
    logic.media_count = max_index

    # Tempにリストを保持する準備をします.
    name = TEXT_LOGIC_NAME.format(logic.pk)
    temp = None

    try:
        # TempからObjectを持ってきます.
        temp = Temp.objects.get(name=name)

    except Temp.DoesNotExist:

        # 存在しなかった場合は新規に作成します.
        temp = Temp.objects.create()
        temp.name = name

    # Tempにリストを保存します.
    temp.content = " ".join(map(str, text_list))
    temp.save()

    # 実行終了の情報をstateに書いておきます.
    add_state(logic, "text_prep finished.")


def text_get_content(trial, seq):
    """text_prep()で準備された結果に基づいて表示すべきテキストを決定します.

    指定された連番に対応するテキストを返却します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
        seq (int): 要求しているメディアの連番.

    Raises:
        Http404: 該当するテキストが見つからなかった場合.

    Returns:
        (Json) メディアの型(TXT)とデータ(テキスト)が示されたJsonデータ.
    """

    # 実行中のTrialに結び付けられているLogicを取得します.
    logic = trial.logic

    # そのLogicが持っているインデックスのリストを取得します.
    index_list = logic.media_list.split()
    index_count = len(index_list)

    # 表示すべきデータが一個もない場合はエラーにはせずにメッセージを出すようにします.
    if index_count == 0:
        return json.dumps({"type": "txt", "data": "No data to show"})

    # Tempからリストを撮ってきます.
    name = TEXT_LOGIC_NAME.format(logic.pk)
    temp = Temp.objects.get(name=name)
    text_list = temp.content.split()

    # seq番目のTextsをとってきます.
    text = text_list[int(index_list[int(seq) % index_count])]

    # jsonを返します.
    return json.dumps({"type": "txt", "data": text})


def blank_prep(logic):
    """何も表示しないLogicを準備します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
    """

    # 実行開始の情報をstateに書いておきます.
    add_state(logic, "blank_prep started.")

    pass

    # 実行終了の情報をstateに書いておきます.
    add_state(logic, "blank_prep finished.")


def blank_get_content(trial, seq):
    """何も表示しません.

    常に何も表示しないという情報を返却します.

    Args:
        logic (Logic): 対象となるLogicのインスタンス.
        seq (int): 要求しているメディアの連番.

    Raises:
        Http404: 該当するテキストが見つからなかった場合.

    Returns:
        (Json) メディアの型(TXT)とデータ(テキスト)が示されたJsonデータ.
    """

    return json.dumps({"type": "txt", "data": ""})
