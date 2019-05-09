import networkx


class Election:
    """
    A user adds votes to the election and can retrieve results from the election.
    """

    def __init__(self, votes):
        """
        :param votes: An array of votes, where a vote is any indexable object of length 3
                Each vote looks like this: ["Alice",  "Bob", "won"] which indicates that "Alice" lost to "Bob".
        """
        assert self.__are_valid_votes(votes)
        self._votes = list(votes)
        self._candidates = self.__get_all_candidates_from_votes(self._votes)

    def get_victory_graph(self) -> networkx.DiGraph:
        """A victory graph is a matchup graph of each candidate, but with only edges for wins. Every out-edge represents
         a win over another candidate. Two candidates will not have any edge between them if there is a perfect tie by
         win ratio.

        See `get_matchup_graph` for a description of the attributes on nodes and edges.
         """
        matchups = self.get_matchup_graph()
        edges_to_remove = []
        for u, v in matchups.edges:
            margin_u_to_v = matchups.get_edge_data(u, v)["margin"]
            margin_v_to_u = matchups.get_edge_data(v, u)["margin"]

            # u->v has lower win margin than v->u, keep the "winning edge" with higher win ratio
            # this will remove both if there is a perfect tie - but that's okay
            if margin_u_to_v <= margin_v_to_u:
                edges_to_remove.append((u, v))

        matchups.remove_edges_from(edges_to_remove)
        return matchups

    def get_matchup_graph(self) -> networkx.DiGraph:
        """A matchup graph is a fully-connected graph, with each out-edge corresponding to a matchup and each in-edge
        corresponding to the same matchup, but with wins and losses flipped. An edge `(a, b)` from a to b will have
        `wins` corresponding to the number of wins `a` has over `b`, while the edge `(b, a)` will have `wins`
        corresponding to the number of wins `b` has over `a`.

        Every edge has the attributes `wins` (described above), `losses`, `ties`, and `margin`. `losses` and `ties` are
        self explanatory, simply the number of losses or ties between the two candidates. `margin` is the ratio of
        wins to overall votes.
        """
        matchups = self.get_matchups()
        ids = matchups.keys()

        g = networkx.DiGraph()
        g.add_nodes_from(ids)
        for candidate1 in matchups:
            for candidate2 in matchups[candidate1]:
                candidate1to2 = matchups[candidate1][candidate2]
                total_votes_candidate1to2 = sum(candidate1to2.values())
                if total_votes_candidate1to2 != 0:
                    g.add_edge(candidate1, candidate2,
                               wins=candidate1to2["wins"],
                               losses=candidate1to2["losses"],
                               ties=candidate1to2["ties"],
                               margin=candidate1to2["wins"] / total_votes_candidate1to2)

                candidate2to1 = matchups[candidate2][candidate1]
                total_votes_candidate2to1 = sum(candidate2to1.values())
                if total_votes_candidate2to1 != 0:
                    g.add_edge(candidate2, candidate1,
                               wins=candidate2to1["wins"],
                               losses=candidate2to1["losses"],
                               ties=candidate2to1["ties"],
                               margin=candidate2to1["wins"] / total_votes_candidate2to1)

        return g

    def get_matchups(self) -> dict:
        """This matchup shows the number of wins and losses each candidate has against each other.
        The shape of the final dictionary returned is:

         >>> {\
            "candidate1": { \
                 {"candidate2": {"win": 12, "loss": 10, "tie": 5}}, \
                 {"candidate3": {"win": 3,  "loss": 23, "tie": 9}}, \
                 # potentially many more \
             }, \
             "candidate2": { \
                 {"candidate1": {"win": 10, "loss": 12, "tie": 5}}, \
                 {"candidate3": {"win": 23, "loss":  3, "tie": 9}}, \
                 # potentially many more \
             },\
             # and so on\
          }

        :return: a matchup mapping, as described above
        """
        matchups = {}
        for candidate in self._candidates:
            matchups[candidate] = {}
        for candidate1 in self._candidates:
            for candidate2 in self._candidates:
                if candidate1 == candidate2:
                    continue
                matchups[candidate1][candidate2] = {"wins": 0, "losses": 0, "ties": 0}
                matchups[candidate2][candidate1] = {"wins": 0, "losses": 0, "ties": 0}

        for vote in self._votes:
            candidate1, candidate2, result = vote
            if result == "win":
                matchups[candidate1][candidate2]["wins"] += 1
                matchups[candidate2][candidate1]["losses"] += 1
            if result == "loss":
                matchups[candidate1][candidate2]["losses"] += 1
                matchups[candidate2][candidate1]["wins"] += 1
            if result == "tie":
                matchups[candidate1][candidate2]["ties"] += 1
                matchups[candidate2][candidate1]["ties"] += 1

        return matchups

    ####################################################################################################################
    # Ranking Methods

    def ranking_by_ranked_pairs(self) -> list:
        matchups = self.get_victory_graph()

        g = networkx.DiGraph()
        g.add_nodes_from(matchups.nodes)

        edges = [(u, v, matchups.get_edge_data(u, v)) for (u, v) in matchups.edges]
        edges.sort(key=lambda x: x[2]["margin"], reverse=True)
        for u, v, data in edges:
            g.add_edge(u, v, **data)
            try:
                networkx.find_cycle(g)
                g.remove_edge(u, v)
            except networkx.NetworkXNoCycle:
                pass

        assert networkx.is_directed_acyclic_graph(g)
        return list(networkx.topological_sort(g))


    def ranking_by_copeland(self) -> list:
        g = self.get_victory_graph()
        return sorted([(n, g.out_degree(n) - g.in_degree(n)) for n in g.nodes], key=lambda x: x[1], reverse=True)

    def ranking_by_minimax(self) -> list:
        g = self.get_matchup_graph()
        return sorted(g.nodes, key=lambda n: max(g.get_edge_data(u, v)["margin"] for u, v in g.in_edges(n)))

    def ranking_by_win_ratio(self) -> list:
        matchups = self.get_matchups()

        wins_and_ties_vs_losses = {}
        for candidate in matchups:
            wins_and_ties_vs_losses[candidate] = [0, 0]
            for matchup in matchups[candidate]:
                wins = matchups[candidate][matchup]["wins"]
                losses = matchups[candidate][matchup]["losses"]
                wins_and_ties_vs_losses[candidate][0] += wins
                wins_and_ties_vs_losses[candidate][1] += losses

        ratios = [(candidate, (x[0] / ((x[0] + x[1]) or float("inf"))))
                  for candidate, x in wins_and_ties_vs_losses.items()]
        return sorted(ratios, key=lambda x: x[1], reverse=True)

    def ranking_by_win_tie_ratio(self) -> list:
        matchups = self.get_matchups()

        wins_and_ties_vs_losses = {}
        for candidate in matchups:
            wins_and_ties_vs_losses[candidate] = [0, 0]
            for matchup in matchups[candidate]:
                wins = matchups[candidate][matchup]["wins"]
                ties = matchups[candidate][matchup]["ties"]
                losses = matchups[candidate][matchup]["losses"]
                wins_and_ties_vs_losses[candidate][0] += wins + ties
                wins_and_ties_vs_losses[candidate][1] += losses

        ratios = [(candidate, (x[0] / ((x[0] + x[1]) or float("inf"))))
                  for candidate, x in wins_and_ties_vs_losses.items()]
        return sorted(ratios, key=lambda x: x[1], reverse=True)


    @staticmethod
    def __get_all_candidates_from_votes(votes) -> set:
        """
        :return: All the candidates mentioned in the votes
        """
        return {vote[0] for vote in votes} | {vote[1] for vote in votes}

    @staticmethod
    def __are_valid_votes(votes: iter) -> bool:
        return all(len(vote) == 3 and vote[2] in {"win", "loss", "tie"} for vote in votes)
