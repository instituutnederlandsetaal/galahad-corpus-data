# read .env
set -a && source .env && set +a

PGPASSWORD=$PASS \
    psql -h $HOST -U $USER -d gig_pro -At -F $'\t' \
    -c "SELECT DISTINCT modern_lemma, SPLIT_PART(lemma_gigpos,'(',1) FROM data.lemmata" > lexicon.tsv

PGPASSWORD=$PASS \
    psql -h $HOST -U $USER -d gigant_hilex_candidate -At -F $'\t' \
    -c "SELECT DISTINCT modern_lemma, lemma_part_of_speech FROM data.lemmata" >> lexicon.tsv

sed  -i 's/NOU-C NOU-P/NOU-C/g' lexicon.tsv
sed  -i 's/NOU-P NOU-C/NOU-C/g' lexicon.tsv
sed  -i 's/PD ART/PD/g' lexicon.tsv

sort -u lexicon.tsv -o lexicon.tsv
