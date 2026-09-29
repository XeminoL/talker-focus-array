`timescale 1ns / 1ps

module fir_decimator #(
    parameter TAPS       = 121,
    parameter RATIO      = 3,
    parameter DATA_WIDTH = 24,
    parameter COEF_WIDTH = 18,
    parameter COEF_FILE  = "fir_coefficients.hex"
) (
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         in_valid,
    input  wire signed [DATA_WIDTH-1:0] in_sample,
    output reg                          out_valid,
    output reg  signed [DATA_WIDTH-1:0] out_sample
);

    localparam INDEX_WIDTH = $clog2(TAPS);
    localparam PHASE_WIDTH = (RATIO > 1) ? $clog2(RATIO) : 1;
    localparam ACC_WIDTH   = DATA_WIDTH + COEF_WIDTH + INDEX_WIDTH;
    localparam SHIFT       = COEF_WIDTH - 1;

    localparam IDLE   = 2'd0;
    localparam RUN    = 2'd1;
    localparam DRAIN  = 2'd2;
    localparam FINISH = 2'd3;

    localparam signed [ACC_WIDTH-1:0] OUT_MAX = (1 <<< (DATA_WIDTH - 1)) - 1;
    localparam signed [ACC_WIDTH-1:0] OUT_MIN = -(1 <<< (DATA_WIDTH - 1));

    reg signed [COEF_WIDTH-1:0] coefficient [0:TAPS-1];
    reg signed [DATA_WIDTH-1:0] history     [0:TAPS-1];

    integer clear_index;

    initial begin
        $readmemh(COEF_FILE, coefficient);
        for (clear_index = 0; clear_index < TAPS; clear_index = clear_index + 1)
            history[clear_index] = 0;
    end

    reg [INDEX_WIDTH-1:0] write_index;
    reg [INDEX_WIDTH-1:0] newest;
    reg [PHASE_WIDTH-1:0] phase;
    reg [1:0]             state;
    reg [INDEX_WIDTH-1:0] tap;
    reg [1:0]             drain_count;

    reg                          read_valid;
    reg signed [DATA_WIDTH-1:0]  read_sample;
    reg signed [COEF_WIDTH-1:0]  read_coefficient;
    reg                          product_valid;
    reg signed [DATA_WIDTH+COEF_WIDTH-1:0] product;
    reg signed [ACC_WIDTH-1:0]   accumulator;

    wire [INDEX_WIDTH-1:0] read_index = (newest >= tap) ? newest - tap : newest + TAPS - tap;
    wire signed [ACC_WIDTH-1:0] scaled = accumulator >>> SHIFT;

    always @(posedge clk) begin
        if (rst) begin
            write_index <= 0;
            phase       <= 0;
        end else if (in_valid) begin
            history[write_index] <= in_sample;
            write_index <= (write_index == TAPS - 1) ? 0 : write_index + 1'b1;
            phase       <= (phase == RATIO - 1) ? 0 : phase + 1'b1;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            state         <= IDLE;
            tap           <= 0;
            newest        <= 0;
            drain_count   <= 0;
            read_valid    <= 1'b0;
            product_valid <= 1'b0;
            accumulator   <= 0;
            out_valid     <= 1'b0;
            out_sample    <= 0;
        end else begin
            out_valid        <= 1'b0;
            read_valid       <= 1'b0;
            read_sample      <= history[read_index];
            read_coefficient <= coefficient[tap];
            product_valid    <= read_valid;
            product          <= read_sample * read_coefficient;
            if (product_valid)
                accumulator <= accumulator + product;

            case (state)
                IDLE: begin
                    if (in_valid && phase == RATIO - 1) begin
                        newest      <= write_index;
                        tap         <= 0;
                        accumulator <= 0;
                        state       <= RUN;
                    end
                end
                RUN: begin
                    read_valid <= 1'b1;
                    if (tap == TAPS - 1) begin
                        drain_count <= 0;
                        state       <= DRAIN;
                    end else begin
                        tap <= tap + 1'b1;
                    end
                end
                DRAIN: begin
                    drain_count <= drain_count + 1'b1;
                    if (drain_count == 2'd2)
                        state <= FINISH;
                end
                FINISH: begin
                    out_valid  <= 1'b1;
                    out_sample <= (scaled > OUT_MAX) ? OUT_MAX[DATA_WIDTH-1:0] :
                                  (scaled < OUT_MIN) ? OUT_MIN[DATA_WIDTH-1:0] :
                                  scaled[DATA_WIDTH-1:0];
                    state      <= IDLE;
                end
            endcase
        end
    end

endmodule
