from wtforms.validators import ValidationError


class Unique(object):
    # Shout out to exploreflask.com for this approach
    def __init__(self, model, field, message=u'This element already exists.'):
        self.model = model
        self.field = field
        self.message = message

    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            if form.is_edit:
                pass
            else:
                raise ValidationError(self.message)
