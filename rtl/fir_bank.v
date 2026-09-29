`timescale 1ns / 1ps

module fir_bank #(
    parameter CHANNELS   = 64,
    parameter TAPS       = 121,
    parameter RATIO      = 3,
    parameter DATA_WIDTH = 24,
    parameter COEF_WIDTH = 18,
    parameter ACC_WIDTH  = 48,
    parameter COEF_FILE  = "fir_coefficients.hex"
) (
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         in_valid,
    input  wire [$clog2(CHANNELS)-1:0]  in_channel,
    input  wire signed [DATA_WIDTH-1:0] in_sample,
    output reg                          out_valid,
    output reg  [$clog2(CHANNELS)-1:0]  out_channel,
    output reg  signed [DATA_WIDTH-1:0] out_sample
);

    localparam CHANNEL_WIDTH = $clog2(CHANNELS);
    localparam SLOT_WIDTH    = $clog2(TAPS + RATIO);
    localparam SLOTS         = 1 << SLOT_WIDTH;
    localparam HALF          = (TAPS - 1) / 2;
    localparam TAP_WIDTH     = $clog2(HALF + 1);
    localparam PHASE_WIDTH   = (RATIO > 1) ? $clog2(RATIO) : 1;
    localparam DEPTH         = CHANNELS * SLOTS;
    localparam SHIFT         = COEF_WIDTH - 1;
    localparam SUM_WIDTH     = DATA_WIDTH + 1;
    localparam PRODUCT_WIDTH = SUM_WIDTH + COEF_WIDTH;

    localparam signed [ACC_WIDTH-1:0] OUT_MAX = (1 <<< (DATA_WIDTH - 1)) - 1;
    localparam signed [ACC_WIDTH-1:0] OUT_MIN = -(1 <<< (DATA_WIDTH - 1));

    reg signed [DATA_WIDTH-1:0] newer_ram [0:DEPTH-1];
    reg signed [DATA_WIDTH-1:0] older_ram [0:DEPTH-1];
    reg signed [COEF_WIDTH-1:0] coefficient [0:TAPS-1];

    integer clear_index;

    initial begin
        $readmemh(COEF_FILE, coefficient);
        for (clear_index = 0; clear_index < DEPTH; clear_index = clear_index + 1) begin
            newer_ram[clear_index] = 0;
            older_ram[clear_index] = 0;
        end
    end

    reg [SLOT_WIDTH-1:0]    write_slot;
    reg [PHASE_WIDTH-1:0]   phase;
    reg [SLOT_WIDTH-1:0]    newest;
    reg                     running;
    reg [CHANNEL_WIDTH-1:0] channel;
    reg [TAP_WIDTH-1:0]     tap;

    wire frame_end = in_valid && in_channel == CHANNELS - 1;
    wire last_tap  = tap == HALF;
    wire [SLOT_WIDTH-1:0] newer_slot = newest - tap;
    wire [SLOT_WIDTH-1:0] older_slot = newest - (TAPS - 1) + tap;

    always @(posedge clk) begin
        if (in_valid) begin
            newer_ram[{in_channel, write_slot}] <= in_sample;
            older_ram[{in_channel, write_slot}] <= in_sample;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            write_slot <= 0;
            phase      <= 0;
        end else if (frame_end) begin
            write_slot <= write_slot + 1'b1;
            phase      <= (phase == RATIO - 1) ? 0 : phase + 1'b1;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            running <= 1'b0;
            channel <= 0;
            tap     <= 0;
            newest  <= 0;
        end else if (!running) begin
            if (frame_end && phase == RATIO - 1) begin
                running <= 1'b1;
                channel <= 0;
                tap     <= 0;
                newest  <= write_slot;
            end
        end else if (last_tap) begin
            tap <= 0;
            if (channel == CHANNELS - 1)
                running <= 1'b0;
            else
                channel <= channel + 1'b1;
        end else begin
            tap <= tap + 1'b1;
        end
    end

    reg                         read_valid, read_first, read_last, read_middle;
    reg [CHANNEL_WIDTH-1:0]     read_channel;
    reg [TAP_WIDTH-1:0]         read_tap;
    reg signed [DATA_WIDTH-1:0] newer_sample, older_sample;

    always @(posedge clk) begin
        newer_sample <= newer_ram[{channel, newer_slot}];
        older_sample <= older_ram[{channel, older_slot}];
        read_valid   <= running && !rst;
        read_first   <= tap == 0;
        read_last    <= last_tap;
        read_middle  <= last_tap;
        read_channel <= channel;
        read_tap     <= tap;
    end

    reg                          sum_valid, sum_first, sum_last;
    reg [CHANNEL_WIDTH-1:0]      sum_channel;
    reg signed [SUM_WIDTH-1:0]   sum;
    reg signed [COEF_WIDTH-1:0]  sum_coefficient;

    always @(posedge clk) begin
        sum             <= read_middle ? newer_sample : newer_sample + older_sample;
        sum_coefficient <= coefficient[read_tap];
        sum_valid       <= read_valid;
        sum_first       <= read_first;
        sum_last        <= read_last;
        sum_channel     <= read_channel;
    end

    reg                            product_valid, product_first, product_last;
    reg [CHANNEL_WIDTH-1:0]        product_channel;
    reg signed [PRODUCT_WIDTH-1:0] product;

    always @(posedge clk) begin
        product         <= sum * sum_coefficient;
        product_valid   <= sum_valid;
        product_first   <= sum_first;
        product_last    <= sum_last;
        product_channel <= sum_channel;
    end

    reg  signed [ACC_WIDTH-1:0] accumulator;
    wire signed [ACC_WIDTH-1:0] total  = (product_first ? 0 : accumulator) + product;
    wire signed [ACC_WIDTH-1:0] scaled = total >>> SHIFT;

    always @(posedge clk) begin
        if (rst) begin
            accumulator <= 0;
            out_valid   <= 1'b0;
            out_channel <= 0;
            out_sample  <= 0;
        end else begin
            out_valid <= 1'b0;
            if (product_valid) begin
                accumulator <= total;
                if (product_last) begin
                    out_valid   <= 1'b1;
                    out_channel <= product_channel;
                    out_sample  <= (scaled > OUT_MAX) ? OUT_MAX[DATA_WIDTH-1:0] :
                                   (scaled < OUT_MIN) ? OUT_MIN[DATA_WIDTH-1:0] :
                                   scaled[DATA_WIDTH-1:0];
                end
            end
        end
    end

endmodule
