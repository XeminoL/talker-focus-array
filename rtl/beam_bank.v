`timescale 1ns / 1ps

module beam_bank #(
    parameter CHANNELS   = 64,
    parameter TAPS       = 64,
    parameter DATA_WIDTH = 24,
    parameter COEF_WIDTH = 18,
    parameter ACC_WIDTH  = 56
) (
    input  wire                                       clk,
    input  wire                                       rst,
    input  wire                                       coef_write,
    input  wire [$clog2(CHANNELS)+$clog2(TAPS)-1:0]   coef_address,
    input  wire signed [COEF_WIDTH-1:0]               coef_data,
    input  wire [5:0]                                 shift,
    input  wire                                       in_valid,
    input  wire [$clog2(CHANNELS)-1:0]                in_channel,
    input  wire signed [DATA_WIDTH-1:0]               in_sample,
    output reg                                        out_valid,
    output reg  signed [DATA_WIDTH-1:0]               out_sample
);

    localparam CHANNEL_WIDTH = $clog2(CHANNELS);
    localparam TAP_WIDTH     = $clog2(TAPS);
    localparam SLOT_WIDTH    = TAP_WIDTH + 1;
    localparam DEPTH         = CHANNELS << SLOT_WIDTH;
    localparam PRODUCT_WIDTH = DATA_WIDTH + COEF_WIDTH;

    localparam signed [ACC_WIDTH-1:0] OUT_MAX = (1 <<< (DATA_WIDTH - 1)) - 1;
    localparam signed [ACC_WIDTH-1:0] OUT_MIN = -(1 <<< (DATA_WIDTH - 1));

    reg signed [DATA_WIDTH-1:0] history     [0:DEPTH-1];
    reg signed [COEF_WIDTH-1:0] coefficient [0:CHANNELS*TAPS-1];

    integer clear_index;

    initial begin
        for (clear_index = 0; clear_index < DEPTH; clear_index = clear_index + 1)
            history[clear_index] = 0;
        for (clear_index = 0; clear_index < CHANNELS * TAPS; clear_index = clear_index + 1)
            coefficient[clear_index] = 0;
    end

    always @(posedge clk)
        if (coef_write)
            coefficient[coef_address] <= coef_data;

    reg [SLOT_WIDTH-1:0] write_slot;
    reg [SLOT_WIDTH-1:0] newest;

    always @(posedge clk) begin
        if (in_valid)
            history[{in_channel, write_slot}] <= in_sample;
    end

    wire frame_end = in_valid && in_channel == CHANNELS - 1;

    always @(posedge clk) begin
        if (rst)
            write_slot <= 0;
        else if (frame_end)
            write_slot <= write_slot + 1'b1;
    end

    reg                     running;
    reg [CHANNEL_WIDTH-1:0] channel;
    reg [TAP_WIDTH-1:0]     tap;

    wire last_step = channel == CHANNELS - 1 && tap == TAPS - 1;
    wire [SLOT_WIDTH-1:0] read_slot = newest - tap;

    always @(posedge clk) begin
        if (rst) begin
            running <= 1'b0;
            channel <= 0;
            tap     <= 0;
            newest  <= 0;
        end else if (!running) begin
            if (frame_end) begin
                running <= 1'b1;
                channel <= 0;
                tap     <= 0;
                newest  <= write_slot;
            end
        end else begin
            tap <= tap + 1'b1;
            if (tap == TAPS - 1)
                channel <= channel + 1'b1;
            if (last_step)
                running <= 1'b0;
        end
    end

    reg                         read_valid, read_first, read_last;
    reg signed [DATA_WIDTH-1:0] read_sample;
    reg signed [COEF_WIDTH-1:0] read_coefficient;

    always @(posedge clk) begin
        read_sample      <= history[{channel, read_slot}];
        read_coefficient <= coefficient[{channel, tap}];
        read_valid       <= running && !rst;
        read_first       <= channel == 0 && tap == 0;
        read_last        <= last_step;
    end

    reg                            product_valid, product_first, product_last;
    reg signed [PRODUCT_WIDTH-1:0] product;

    always @(posedge clk) begin
        product       <= read_sample * read_coefficient;
        product_valid <= read_valid;
        product_first <= read_first;
        product_last  <= read_last;
    end

    reg  signed [ACC_WIDTH-1:0] accumulator;
    wire signed [ACC_WIDTH-1:0] total = (product_first ? 0 : accumulator) + product;

    reg                         final_valid;
    reg  signed [ACC_WIDTH-1:0] final_total;
    reg                         shifted_valid;
    reg  signed [ACC_WIDTH-1:0] shifted;

    always @(posedge clk) begin
        if (rst) begin
            accumulator   <= 0;
            final_valid   <= 1'b0;
            final_total   <= 0;
            shifted_valid <= 1'b0;
            shifted       <= 0;
            out_valid     <= 1'b0;
            out_sample    <= 0;
        end else begin
            final_valid <= product_valid && product_last;
            if (product_valid) begin
                accumulator <= total;
                if (product_last)
                    final_total <= total;
            end
            shifted_valid <= final_valid;
            shifted       <= final_total >>> shift;
            out_valid     <= shifted_valid;
            if (shifted_valid)
                out_sample <= (shifted > OUT_MAX) ? OUT_MAX[DATA_WIDTH-1:0] :
                              (shifted < OUT_MIN) ? OUT_MIN[DATA_WIDTH-1:0] :
                              shifted[DATA_WIDTH-1:0];
        end
    end

endmodule
