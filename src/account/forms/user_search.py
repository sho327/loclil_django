from django import forms


class UserSearchForm(forms.Form):
    """
    ユーザー検索フォーム
    """

    search_word = forms.CharField(
        required=False,
        max_length=100,
        label="ユーザー名、スキル",
        widget=forms.TextInput(
            attrs={
                "placeholder": "例: React, Python, Taro Yamada",
                "class": "input input-bordered w-full",
            }
        ),
    )

    location = forms.CharField(
        required=False,
        max_length=100,
        label="所在地",
        widget=forms.TextInput(
            attrs={
                "placeholder": "例: 東京",
                "class": "input input-bordered w-full",
            }
        ),
    )

    skill_tag = forms.CharField(
        required=False,
        max_length=100,
        label="スキルタグ",
        widget=forms.TextInput(
            attrs={
                "placeholder": "例: Python",
                "class": "input input-bordered w-full",
            }
        ),
    )

    def clean_search_word(self):
        """search_wordのバリデーション"""
        search_word = self.cleaned_data.get("search_word", "").strip()
        return search_word if search_word else None

    def clean_location(self):
        """locationのバリデーション"""
        location = self.cleaned_data.get("location", "").strip()
        return location if location else None

    def clean_skill_tag(self):
        """skill_tagのバリデーション"""
        skill_tag = self.cleaned_data.get("skill_tag", "").strip()
        return skill_tag if skill_tag else None
