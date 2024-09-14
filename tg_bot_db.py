import sqlalchemy
import sqlalchemy as sq
# from sqlalchemy import func, or_, and_
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    tg_id = sq.Column(sq.Integer, primary_key=True)

    def __str__(self):
        return f'User id {self.tg_id}'


class TargetWord(Base):
    __tablename__ = 'target_word'

    id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String(length=40), nullable=False)
    user_tg_id = sq.Column(sq.Integer, sq.ForeignKey('users.tg_id'), nullable=False)

    user = relationship('User', backref='target_words')

    def __str__(self):
        return f'Target word {self.id}: ({self.word}, {self.user_tg_id})'


class Translate(Base):
    __tablename__ = 'translate'

    id = sq.Column(sq.Integer, primary_key=True)
    translate = sq.Column(sq.String(length=40), nullable=False)
    target_word_id = sq.Column(sq.Integer, sq.ForeignKey('target_word.id'), nullable=False, unique=True)

    target_word = relationship('TargetWord', backref='translates')

    def __str__(self):
        return f'Translate {self.id}: ({self.translate}, {self.target_word_id})'


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


DSN = "postgresql://postgres:postgres@localhost:5432/tg_bot_db"
engine = sqlalchemy.create_engine(DSN)

Session = sessionmaker(bind=engine)
session = Session()

if __name__ == '__main__':
    # create_tables(engine)
    #
    # user_zero = User(tg_id=0)
    # session.add(user_zero)
    # session.commit()
    #
    # word1 = TargetWord(word='Justice', user_tg_id=0)
    # word2 = TargetWord(word='District', user_tg_id=0)
    # word3 = TargetWord(word='Addiction', user_tg_id=0)
    # word4 = TargetWord(word='Challenge', user_tg_id=0)
    # word5 = TargetWord(word='Condition', user_tg_id=0)
    # word6 = TargetWord(word='Responsibility', user_tg_id=0)
    # word7 = TargetWord(word='Wisdom', user_tg_id=0)
    # word8 = TargetWord(word='Suggestion', user_tg_id=0)
    # word9 = TargetWord(word='Amazing', user_tg_id=0)
    # word10 = TargetWord(word='Engaging', user_tg_id=0)
    # session.add_all([word1, word2, word3, word4, word5, word6, word7, word8, word9, word10])
    # session.commit()
    #
    # translate1 = Translate(translate='Справедливость', target_word_id=1)
    # translate2 = Translate(translate='Район', target_word_id=2)
    # translate3 = Translate(translate='Зависимость', target_word_id=3)
    # translate4 = Translate(translate='Вызов, сложность', target_word_id=4)
    # translate5 = Translate(translate='Состояние', target_word_id=5)
    # translate6 = Translate(translate='Ответственность', target_word_id=6)
    # translate7 = Translate(translate='Мудрость', target_word_id=7)
    # translate8 = Translate(translate='Предложение', target_word_id=8)
    # translate9 = Translate(translate='Изумительный', target_word_id=9)
    # translate10 = Translate(translate='Вовлекающий', target_word_id=10)
    # session.add_all([translate1, translate2, translate3, translate4, translate5, translate6, translate7, translate8,
    #                  translate9, translate10])
    # session.commit()

    session.close()
