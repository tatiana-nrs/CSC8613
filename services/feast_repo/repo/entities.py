from feast import Entity

# TODO: définir l'entité principale "user"
user = Entity(
    name="user",               # TODO
    join_keys=["user_id"],        # TODO
    description="Représente un client unique de StreamFlow identifié par son user_id.",        # TODO (en français)
)