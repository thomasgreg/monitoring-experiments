from pathlib import Path
from time import sleep
import click


@click.command()
@click.argument('inpath')
@click.argument('outpath')
@click.option('--period', default=1.)
def main(inpath, outpath, period):
    """Utility to pipe one file to another for playback of results"""
    if Path(outpath).exists():
        with open(outpath, 'r') as f:
            n = len(f.readlines())
    else:
        n = 0

    with open(outpath, 'a') as outfile:
        with open(inpath, 'r') as infile:
            lines = infile.readlines()

            for line in lines[n:]:
                outfile.write(line)
                outfile.flush()
                sleep(period)


if __name__ == '__main__':
    main()
