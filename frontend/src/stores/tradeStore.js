import { defineStore } from "pinia"
import axios from "axios"

const API = "http://localhost:9000"

export const useTradeStore = defineStore(
    "trade",
    {
        state: () => ({

            profit: {},

            closedProfit: {},

            profitCurve: [],

            balanceCurve: [],

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


            // 高频刷新
            async refresh() {


                try {

                    const [
                        profit,
                        positions,
                        summary,
                        floating
                    ] = await Promise.all([


                        axios.get(
                            `${API}/position/profit`
                        ),


                        axios.get(
                            `${API}/position/open`
                        ),


                        axios.get(
                            `${API}/position/summary`
                        ),


                        axios.get(
                            `${API}/position/floating`
                        )

                    ])



                    this.profit =
                        profit.data


                    this.positions =
                        positions.data


                    this.summary =
                        summary.data


                    this.floating =
                        floating.data



                } catch(e){

                    console.error(
                        "refresh error",
                        e.response?.data || e
                    )

                }

            },



            // 低频刷新
            async refreshHistory(){


                try {

                    const [
                        closed,
                        closedProfit,
                        profitCurve,
                        balanceCurve
                    ] = await Promise.all([

                        axios.get(
                            `${API}/position/closed`
                        ),

                        axios.get(
                            `${API}/position/closed_profit`
                        ),

                        axios.get(
                            `${API}/position/profit_curve`
                        ),

                        axios.get(
                            `${API}/position/balance_curve`
                        )

                    ])

                    this.closedPositions =
                        closed.data

                    this.closedProfit =
                        closedProfit.data

                    this.profitCurve =
                        profitCurve.data

                    this.balanceCurve =
                        balanceCurve.data

                } catch(e){


                    console.error(
                        "history error",
                        e.response?.data || e
                    )


                }


            }

        }
    }
)