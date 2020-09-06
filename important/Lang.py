class Lang:
    def __init__(self, language):
        if language == "ע" or language == "he":
            self.language = "he"
        elif language == "":
            self.language = "en"
        else:
            print("that's not an option")
            while True:
                language = input("if the song is in hebrew write he or ע, else enter")
                if language == "ע" or language == "he":
                    self.language = "he"
                    break
                elif language == "":
                    self.language = "en"
                    break

    def lyrics(self):
        if self.language == "he":
            return "מילים"
        return "lyrics"

    def songs(self):
        if self.language == "he":
            return "שירים"
        return "songs"

    def title(self):
        if self.language == "he":
            return "שם"
        return "title"

    def length(self):
        if self.language == "he":
            return "משך"
        return "length"
