import { defineStore } from "pinia"
import axios from "axios"

const API = "http://localhost:9000"

export const useTradeStore = defineStore(
    "trade",
    {
        state: () => ({
            profit: {},
            count: {},
            summary: {},
            floating: {},
            positions: {
                long: [],
                short: []
            },
            closedPositions: {
                long: [],
                short: []
            }
        }),

        actions: {

            async refresh() {

                try {

                    const profit =
                        await axios.get(
                            `${API}/position/profit`
                        )

                    console.log(
                        "profit:",
                        profit.data
                    )

                    this.profit =
                        profit.data

                } catch (e) {

                    console.error(
                        "profit error",
                        e.response?.data || e
                    )
                }

                try {

                    const count =
                        await axios.get(
                            `${API}/position/count`
                        )

                    console.log(
                        "count:",
                        count.data
                    )

                    this.count =
                        count.data

                } catch (e) {

                    console.error(
                        "count error",
                        e.response?.data || e
                    )
                }

                try {

                    const positions =
                        await axios.get(
                            `${API}/position/open`
                        )

                    console.log(
                        "positions:",
                        positions.data
                    )

                    this.positions =
                        positions.data

                } catch (e) {

                    console.error(
                        "positions error",
                        e.response?.data || e
                    )
                }

                try {

                    const summary =
                        await axios.get(
                            `${API}/position/summary`
                        )

                    this.summary =
                        summary.data

                } catch(e) {

                    console.error(
                        "summary error",
                        e.response?.data || e
                    )
                }

                try {
                    const floating =
                        await axios.get(
                            `${API}/position/floating`
                        )

                    this.floating =
                        floating.data

                } catch(e) {
                    console.error(
                        "floating error",
                        e.response?.data || e
                    )
                }

                try {

                    const closed =
                        await axios.get(
                            `${API}/position/closed`
                        )

                    this.closedPositions =
                        closed.data

                } catch (e) {

                    console.error(
                        "closed error",
                        e.response?.data || e
                    )
                }
            }
        }
    }
)