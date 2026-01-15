class Comic(object):
    def __init__(self, title, publisher, issue, released):
        self.title = title
        self.publisher = publisher
        self.issue = issue
        self.released = released

    def get_Comic(self):
        return{
            "title": self.title,
            "publisher": self.publisher,
            "issue": self.issue,
            "released": self.released
        }
