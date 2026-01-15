class Ticket:
    # class attribute
    ticket_type = "Not Available"

    def __init__(self, issue_id="", summary="", attr={}):
        self.issue_id = issue_id
        self.summary = summary
        self.attr = Ticket_Attributes(attr)

    def print_info(self):
        return {
            "issue_id": format(self.issue_id),
            "summary": format(self.summary),
            "attributes": self.attr.get_attributes()
        }

    def set_issue_id(self, issue_id):
        self.issue_id = issue_id

    def set_issue_id(self, summary):
        self.summary = summary


class Ticket_Attributes:
    def __init__(self, dic):
        self.dic = dic

    def set_attributes(self, dic):
        self.dic = dic

    def get_attributes(self):
        return self.dic
