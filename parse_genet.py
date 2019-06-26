#!/usr/bin/env python

"""
Parse the reference panel, summary statistics, and validation set.

"""


import scipy as sp
from scipy.stats import norm
import h5py


def parse_ref(ref_file, chrom):
    print('... parse reference file: %s ...' % ref_file)

    ref_dict = {'CHR':[], 'SNP':[], 'BP':[], 'A1':[], 'A2':[], 'FRQ_EUR':[], 'FRQ_EAS':[], 'FRQ_AFR':[], 'FLP_EUR':[], 'FLP_EAS':[], 'FLP_AFR':[]}
    with open(ref_file) as ff:
        header = next(ff)
        for line in ff:
            ll = (line.strip()).split()
            if int(ll[0]) == chrom:
                ref_dict['CHR'].append(chrom)
                ref_dict['SNP'].append(ll[1])
                ref_dict['BP'].append(int(ll[2]))
                ref_dict['A1'].append(ll[3])
                ref_dict['A2'].append(ll[4])
                ref_dict['FRQ_EUR'].append(float(ll[5]))
                ref_dict['FRQ_EAS'].append(float(ll[6]))
                ref_dict['FRQ_AFR'].append(float(ll[7]))
                ref_dict['FLP_EUR'].append(int(ll[8]))
                ref_dict['FLP_EAS'].append(int(ll[9]))
                ref_dict['FLP_AFR'].append(int(ll[10]))

    print('... %d SNPs on chromosome %d read from %s ...' % (len(ref_dict['SNP']), chrom, ref_file))
    return ref_dict


def parse_bim(bim_file, chrom):
    print('... parse bim file: %s ...' % (bim_file + '.bim'))

    vld_dict = {'SNP':[], 'A1':[], 'A2':[]}
    with open(bim_file + '.bim') as ff:
        for line in ff:
            ll = (line.strip()).split()
            if int(ll[0]) == chrom:
                vld_dict['SNP'].append(ll[1])
                vld_dict['A1'].append(ll[4])
                vld_dict['A2'].append(ll[5])

    print('... %d SNPs on chromosome %d read from %s ...' % (len(vld_dict['SNP']), chrom, bim_file + '.bim'))
    return vld_dict


def parse_sumstats(ref_dict, vld_dict, sst_file, pop, n_subj):
    print('... parse ' + pop.upper() + ' sumstats file: %s ...' % sst_file)

    sst_dict = {'SNP':[], 'A1':[], 'A2':[]}
    with open(sst_file) as ff:
        header = next(ff)
        for line in ff:
            ll = (line.strip()).split()
            sst_dict['SNP'].append(ll[0])
            sst_dict['A1'].append(ll[1])
            sst_dict['A2'].append(ll[2])

    print('... %d SNPs read from %s ...' % (len(sst_dict['SNP']), sst_file))


    idx = [ii for (ii,frq) in enumerate(ref_dict['FRQ_'+pop.upper()]) if frq>0]
    snp_ref = [ref_dict['SNP'][ii] for ii in idx]
    a1_ref = [ref_dict['A1'][ii] for ii in idx]
    a2_ref = [ref_dict['A2'][ii] for ii in idx]

    ref_snp = set(zip(snp_ref, a1_ref, a2_ref))
    vld_snp = set(zip(vld_dict['SNP'], vld_dict['A1'], vld_dict['A2'])) | set(zip(vld_dict['SNP'], vld_dict['A2'], vld_dict['A1']))
    sst_snp = set(zip(sst_dict['SNP'], sst_dict['A1'], sst_dict['A2'])) | set(zip(sst_dict['SNP'], sst_dict['A2'], sst_dict['A1']))

    comm_snp = ref_snp & vld_snp & sst_snp

    print('... %d common SNPs in the %s reference, %s sumstats, and validation set ...' % (len(comm_snp), pop.upper(), pop.upper()))


    n_sqrt = sp.sqrt(n_subj)
    sst_eff = {}
    with open(sst_file) as ff:
        header = (next(ff).strip()).split()
        header = [col.upper() for col in header]
        for line in ff:
            ll = (line.strip()).split()
            snp = ll[0]; a1 = ll[1]; a2 = ll[2]
            if (snp, a1, a2) in comm_snp:
                if 'BETA' in header:
                    beta = float(ll[3])
                elif 'OR' in header:
                    beta = sp.log(float(ll[3]))

                p = max(float(ll[4]), 1e-323)
                beta_std = sp.sign(beta)*abs(norm.ppf(p/2.0))/n_sqrt
                sst_eff.update({snp: beta_std})
            elif (snp, a2, a1) in comm_snp:
                if 'BETA' in header:
                    beta = float(ll[3])
                elif 'OR' in header:
                    beta = sp.log(float(ll[3]))

                p = max(float(ll[4]), 1e-323)
                beta_std = -1*sp.sign(beta)*abs(norm.ppf(p/2.0))/n_sqrt
                sst_eff.update({snp: beta_std})


    sst_dict = {'CHR':[], 'SNP':[], 'BP':[], 'A1':[], 'A2':[], 'FRQ':[], 'FLP':[], 'BETA':[]}
    for (ii,snp) in enumerate(ref_dict['SNP']):
        if snp in sst_eff:
            sst_dict['SNP'].append(snp)
            sst_dict['CHR'].append(ref_dict['CHR'][ii])
            sst_dict['BP'].append(ref_dict['BP'][ii])
            sst_dict['A1'].append(ref_dict['A1'][ii])
            sst_dict['A2'].append(ref_dict['A2'][ii])
            sst_dict['FRQ'].append(ref_dict['FRQ_'+pop.upper()][ii])
            sst_dict['FLP'].append(ref_dict['FLP_'+pop.upper()][ii])
            sst_dict['BETA'].append(sst_eff[snp])

    return sst_dict


def parse_ldblk(ldblk_dir, sst_dict, pop, chrom):
    print('... parse %s reference LD on chromosome %d ...' % (pop.upper(), chrom))

    chr_name = ldblk_dir + '/ldblk_1kg_' + pop.lower() + '/ldblk_1kg_chr' + str(chrom) + '.hdf5'
    hdf_chr = h5py.File(chr_name, 'r')
    n_blk = len(hdf_chr)
    ld_blk = [sp.array(hdf_chr['blk_'+str(blk)]['ldblk']) for blk in range(1,n_blk+1)]
    snp_blk = [list(hdf_chr['blk_'+str(blk)]['snplist']) for blk in range(1,n_blk+1)]

    blk_size = []
    mm = 0
    for blk in range(n_blk):
        idx = [ii for (ii,snp) in enumerate(snp_blk[blk]) if snp in sst_dict['SNP']]
        blk_size.append(len(idx))
        if idx != []:
            idx_blk = range(mm,mm+len(idx))
            flip = [sst_dict['FLP'][jj] for jj in idx_blk]
            ld_blk[blk] = ld_blk[blk][sp.ix_(idx,idx)]*sp.outer(flip,flip)
            mm += len(idx)
        else:
            ld_blk[blk] = sp.array([])

    return ld_blk, blk_size


def align_ldblk(ref_dict, sst_dict, n_pop, chrom):
    print('... align reference LD on chromosome %d across populations ...' % chrom)

    snp_dict = {'CHR':[], 'SNP':[], 'BP':[], 'A1':[], 'A2':[]}
    for (ii,snp) in enumerate(ref_dict['SNP']):
        for pp in range(n_pop):
            if snp in sst_dict[pp]['SNP']:
                snp_dict['SNP'].append(snp)
                snp_dict['CHR'].append(ref_dict['CHR'][ii])
                snp_dict['BP'].append(ref_dict['BP'][ii])
                snp_dict['A1'].append(ref_dict['A1'][ii])
                snp_dict['A2'].append(ref_dict['A2'][ii])
                break    

    n_snp = len(snp_dict['SNP'])
    print('... %d valid SNPs across populations ...' % n_snp)

    beta_dict = {}
    frq_dict = {}
    idx_dict = {}
    for pp in range(n_pop):
        beta_dict[pp] = sp.array(sst_dict[pp]['BETA'], ndmin=2).T
        frq_dict[pp] = sp.array(sst_dict[pp]['FRQ'], ndmin=2).T
        idx_dict[pp] = [ii for (ii,snp) in enumerate(snp_dict['SNP']) if snp in sst_dict[pp]['SNP']]

    return snp_dict, beta_dict, frq_dict, idx_dict

